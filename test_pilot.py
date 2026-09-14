import unittest
from unittest.mock import patch
from web3 import Web3
import test_payments
import pilot

class PilotTests(unittest.TestCase):
    deploy = test_payments.PaymentTests.deploy
    def setUp(self):
        test_payments.PaymentTests.setUp(self)
        self.arbiter=self.w.eth.accounts[5]
        self.c=self.deploy('AgentNotaryFoundingEscrow',[self.token.address,self.treasury])
        for p in [patch('pilot.connection',return_value=(self.w,self.c)),patch('pilot.USDC',self.token.address),patch.dict('os.environ',{'PILOT_ENABLED':'true'})]:
            p.start(); self.addCleanup(p.stop)

    def post(self,path,data,status=200):
        r=self.client.post('/pilot'+path,json=data)
        self.assertEqual(r.status_code,status,r.text)
        return r.json()

    def send(self,t):
        # Local chain differs; production frontend must retain and check chainId.
        self.assertEqual(t['chainId'],hex(421614))
        t={k:v for k,v in t.items() if k!='chainId'}
        t['value']=int(t.get('value','0x0'),16)
        return self.w.eth.wait_for_transaction_receipt(self.w.eth.send_transaction(t))

    def admit(self):
        self.send(self.post('/prepare-admission',{'caller':self.treasury,'member':self.buyer})['transaction'])

    def proposal(self):
        return self.post('/prepare-proposal',{'buyer':self.buyer,'seller':self.seller,'arbiter':self.arbiter,'amount':'10',
            'salt':'0x'+'11'*32,'terms':'Agreed exact terms','split_bps':4000,'acceptance_window':600,'submit_window':600,'dispute_window':600,'arbitration_window':600})

    def action(self,key,caller,name,**extra):
        return self.post('/deals/'+key+'/prepare-action',{'caller':caller,'action':name,**extra})['transaction']

    def locked(self):
        self.admit(); p=self.proposal(); self.send(p['approval']); self.send(p['proposal']); key=p['deal_id']
        for caller,name in [(self.seller,'sellerAccept'),(self.arbiter,'arbiterAccept')]:
            self.send(self.action(key,caller,name,terms='Agreed exact terms'))
        return key

    def test_free_api_settlement_matches_actual_balances(self):
        before=self.token.functions.balanceOf(self.buyer).call()
        key=self.locked()
        self.send(self.action(key,self.seller,'deliver',content='result',uri='https://example.com/result'))
        self.send(self.action(key,self.buyer,'acceptDelivery'))
        r=self.client.get('/pilot/deals/'+key).json()
        self.assertEqual(r['state'],'ACCEPTED')
        self.assertEqual(r['outcome'],{'payout_units':10000000,'refund_units':0,'fee_units':0,'locked_units':0})
        self.assertEqual(self.token.functions.balanceOf(self.seller).call(),10000000)
        self.assertEqual(self.token.functions.balanceOf(self.buyer).call(),before-10000000)
        self.assertEqual(self.token.functions.balanceOf(self.treasury).call(),0)
        self.post('/deals/'+key+'/prepare-action',{'caller':self.buyer,'action':'acceptDelivery'},409)

    def test_dispute_and_fallback_through_api(self):
        key=self.locked()
        self.send(self.action(key,self.seller,'deliver',content='result',uri='ipfs://result'))
        self.send(self.action(key,self.buyer,'disputeDelivery',reason='Incomplete'))
        self.post('/deals/'+key+'/prepare-action',{'caller':self.other,'action':'resolveSeller'},409)
        self.tester.time_travel(self.w.eth.get_block('latest')['timestamp']+601); self.tester.mine_blocks(1)
        self.send(self.action(key,self.other,'finalizeStalemate'))
        r=self.client.get('/pilot/deals/'+key).json()
        self.assertEqual(r['outcome']['payout_units'],4000000)
        self.assertEqual(r['outcome']['refund_units'],6000000)
        self.assertEqual(self.token.functions.balanceOf(self.c.address).call(),0)

    def test_admission_and_terms_guards(self):
        self.post('/prepare-admission',{'caller':self.other,'member':self.buyer},409)
        self.admit(); p=self.proposal(); self.send(p['approval']); self.send(p['proposal'])
        self.assertTrue(self.post('/deals/'+p['deal_id']+'/verify-terms',{'terms':'Agreed exact terms'})['matches'])
        self.assertFalse(self.post('/deals/'+p['deal_id']+'/verify-terms',{'terms':'different'})['matches'])
        self.post('/deals/'+p['deal_id']+'/prepare-action',{'caller':self.seller,'action':'sellerAccept','terms':'different'},422)
        c=self.client.get('/pilot/config',params={'wallet':self.buyer}).json()
        self.assertTrue(c['member']); self.assertEqual(c['remaining'],49)
        self.assertEqual(p['locked_units'],10000000); self.assertEqual(p['fee_units'],0)

    def test_disabled_unknown_membership_and_assets(self):
        with patch.dict('os.environ',{'PILOT_ENABLED':'false'}):
            c=self.client.get('/pilot/config').json()
            self.assertFalse(c['enabled']); self.assertIsNone(c['remaining']); self.assertIsNone(c['member'])
        deal_id='0x'+'11'*32
        for path in ['/pilot','/pilot/app.js','/pilot/deal/'+deal_id,'/pilot/admin','/pilot/admin.js','/founding50']:
            self.assertEqual(self.client.get(path).status_code,200)

    def test_deployment_is_unsigned_and_testnet_only(self):
        d=self.post('/prepare-deployment',{'deployer':self.buyer,'treasury':self.treasury})
        self.assertEqual(d['transaction']['chainId'],hex(421614))
        receipt=self.send(d['transaction'])
        c=self.w.eth.contract(address=receipt.contractAddress,abi=pilot.ARTIFACT['abi'])
        self.assertEqual(c.functions.FIXED_FEE().call(),0)
        self.assertEqual(c.functions.treasury().call(),self.treasury)
