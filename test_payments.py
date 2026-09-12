import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from eth_abi import encode
from eth_tester import EthereumTester
from web3 import Web3, EthereumTesterProvider
from fastapi.testclient import TestClient
import payments
import main

ROOT = Path(__file__).parent


class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.tester = EthereumTester()
        self.w = Web3(EthereumTesterProvider(self.tester))
        self.buyer, self.seller, self.treasury, self.other = self.w.eth.accounts[:4]
        self.token = self.deploy('TestUSDC', [])
        self.c = self.deploy('AgentNotaryEscrow', [self.token.address, self.treasury])
        self.client = TestClient(main.app)
        self.counter = 0

    def deploy(self, name, args):
        artifact = json.loads((ROOT / 'artifacts' / (name+'.json')).read_text())
        c = self.w.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode'])
        receipt = self.w.eth.wait_for_transaction_receipt(c.constructor(*args).transact({'from':self.buyer}))
        return self.w.eth.contract(address=receipt.contractAddress, abi=artifact['abi'])

    def lock(self, amount=1000000, text=b'accepted result', lifetime=60):
        self.counter += 1
        salt = self.counter.to_bytes(32, 'big')
        key = Web3.keccak(encode(['address','bytes32'],[self.buyer,salt]))
        self.token.functions.approve(self.c.address,amount+5000).transact({'from':self.buyer})
        deadline = self.w.eth.get_block('latest')['timestamp']+lifetime
        self.c.functions.lock(salt,self.seller,amount,Web3.keccak(text),deadline).transact({'from':self.buyer})
        return key, salt, deadline

    def balance(self, who):
        return self.token.functions.balanceOf(who).call()

    def test_success_actual_token_balances(self):
        start=self.balance(self.buyer)
        key,_,_=self.lock(10000000)
        self.assertEqual(self.balance(self.c.address),10005000)
        self.c.functions.deliver(key,b'accepted result').transact({'from':self.seller})
        self.assertEqual(self.balance(self.seller),9850000)
        self.assertEqual(self.balance(self.treasury),155000)
        self.assertEqual(self.balance(self.buyer),start-10005000)
        self.assertEqual(self.balance(self.c.address),0)
        self.assertEqual(self.c.functions.deals(key).call()[-1],2)
        with self.assertRaises(Exception): self.c.functions.deliver(key,b'accepted result').transact({'from':self.seller})

    def test_rejection_actual_refund(self):
        start=self.balance(self.buyer)
        key,_,_=self.lock()
        self.c.functions.deliver(key,b'wrong result').transact({'from':self.seller})
        self.assertEqual(self.balance(self.buyer),start-5000)
        self.assertEqual(self.balance(self.treasury),5000)
        self.assertEqual(self.balance(self.seller),0)
        self.assertEqual(self.c.functions.deals(key).call()[-1],3)

    def test_expiry_full_refund_permissionless(self):
        start=self.balance(self.buyer)
        key,_,deadline=self.lock()
        with self.assertRaises(Exception):self.c.functions.refundExpired(key).transact({'from':self.other})
        self.tester.time_travel(deadline)
        self.tester.mine_blocks(1)
        with self.assertRaises(Exception):self.c.functions.deliver(key,b'accepted result').transact({'from':self.seller})
        self.c.functions.refundExpired(key).transact({'from':self.other})
        self.assertEqual(self.balance(self.buyer),start)
        self.assertEqual(self.balance(self.treasury),0)
        with self.assertRaises(Exception):self.c.functions.refundExpired(key).transact({'from':self.other})

    def test_auth_duplicate_insufficient_and_payload_limits(self):
        key,salt,deadline=self.lock()
        for who in (self.buyer,self.other):
            with self.assertRaises(Exception):self.c.functions.deliver(key,b'accepted result').transact({'from':who})
        with self.assertRaises(Exception):self.c.functions.lock(salt,self.seller,1,Web3.keccak(b'x'),deadline).transact({'from':self.buyer})
        with self.assertRaises(Exception):self.c.functions.lock(b'z'*32,self.seller,1000000,Web3.keccak(b'x'),deadline).transact({'from':self.other})
        for payload in (b'',b'x'*4097):
            with self.assertRaises(Exception):self.c.functions.deliver(key,payload).transact({'from':self.seller})
        self.assertEqual(self.c.functions.deals(key).call()[-1],1)

    def test_quotes_match_integer_contract(self):
        for n in (1,999,10000,1234567,10000000,1000000000):
            q=payments.quote_values(n)
            self.assertEqual(tuple(self.c.functions.quote(n).call()),(q['locked_units'],q['fee_units'],q['payout_units']))
            self.assertEqual(q['locked_units'],q['fee_units']+q['payout_units'])

    def test_isolated_deals_and_no_treasury_sweep(self):
        a,_,_=self.lock(); b,_,_=self.lock(2000000)
        self.c.functions.deliver(a,b'accepted result').transact({'from':self.seller})
        self.assertEqual(self.balance(self.c.address),2005000)
        self.assertEqual(self.c.functions.deals(b).call()[-1],1)

    def test_disabled_api_and_decimal_validation(self):
        with patch.dict(os.environ,{'PAYMENTS_ENABLED':'false'}):
            self.assertFalse(self.client.get('/payments/config').json()['enabled'])
            self.assertEqual(self.client.get('/payments/deals/0x'+'01'*32).status_code,503)
        for value in ('nan','inf','1e2','0','-1','0.0000001','1001'):
            self.assertEqual(self.client.get('/payments/quote',params={'amount':value}).status_code,422)
        self.assertEqual(self.client.get('/payments').status_code,200)

    def test_api_unsigned_transactions_execute_and_read_survives_new_client(self):
        req={'buyer':self.buyer,'seller':self.seller,'amount':'1','salt':'0x'+'aa'*32,'expected_text':'accepted result'}
        with patch.object(payments,'connection',return_value=(self.w,self.c)),patch.object(payments,'USDC',self.token.address):
            p=self.client.post('/payments/prepare-lock',json=req).json()
            for name in ('approval','lock'):
                tx={k:v for k,v in p[name].items() if k!='chainId'}
                self.w.eth.wait_for_transaction_receipt(self.w.eth.send_transaction(tx))
            self.assertEqual(self.client.post('/payments/prepare-lock',json=req).status_code,409)
            self.assertEqual(self.client.post('/payments/deals/'+p['deal_id']+'/prepare-delivery',json={'seller':self.other,'text':'accepted result'}).status_code,409)
            d=self.client.post('/payments/deals/'+p['deal_id']+'/prepare-delivery',json={'seller':self.seller,'text':'accepted result'}).json()
            self.w.eth.wait_for_transaction_receipt(self.w.eth.send_transaction({k:v for k,v in d['transaction'].items() if k!='chainId'}))
            result=TestClient(main.app).get('/payments/deals/'+p['deal_id']).json()
            self.assertEqual(result['state'],'SETTLED')
            self.assertEqual(self.balance(self.treasury),20000)


if __name__=='__main__': unittest.main(verbosity=2)
