"""Founding 50: read-only RPC and unsigned wallet transactions; testnet only."""
import json
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from web3 import Web3
from eth_abi import encode
from payments import ROOT, CHAIN, USDC, address, digest, units, tx, Deploy

ARTIFACT = json.loads((ROOT / 'artifacts/AgentNotaryFoundingEscrow.json').read_text())
router = APIRouter(prefix='/pilot', tags=['Founding 50 testnet'])
STATES = ['NONE','PROPOSED','LOCKED','DELIVERED','DISPUTED','ACCEPTED','RESOLVED_SELLER','RESOLVED_BUYER','FINALIZED_SPLIT','PROPOSAL_EXPIRED','UNDELIVERED_EXPIRED']

def connection():
    if os.getenv('PILOT_ENABLED', 'false').lower() != 'true':
        raise HTTPException(503, 'Pilot contract is not configured. Wallet connection remains available.')
    rpc = os.getenv('PILOT_RPC_URL', '')
    if not rpc.startswith('https://'):
        raise HTTPException(503, 'Configure an HTTPS Arbitrum Sepolia RPC.')
    try:
        w = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout':12}))
        c = w.eth.contract(address=address(os.getenv('PILOT_ESCROW_ADDRESS','')), abi=ARTIFACT['abi'])
        if w.eth.chain_id != CHAIN or not w.eth.get_code(c.address):
            raise ValueError('network or deployment')
        if c.functions.token().call() != USDC or c.functions.treasury().call() != address(os.getenv('PILOT_TREASURY_ADDRESS','')):
            raise ValueError('configuration mismatch')
        if c.functions.FIXED_FEE().call() != 0 or c.functions.MAX_ARBITER_FEE().call() != 0:
            raise ValueError('not free pilot')
        c.functions.memberCount().call()
        return w, c
    except Exception as e:
        raise HTTPException(503, 'Pilot RPC or contract configuration could not be verified.') from e

@router.get('', include_in_schema=False)
def page():
    return FileResponse(ROOT/'static/pilot.html', headers={'Cache-Control':'no-store'})

@router.get('/app.js', include_in_schema=False)
def script():
    return FileResponse(ROOT/'static/pilot.js', media_type='text/javascript', headers={'Cache-Control':'no-store'})

@router.get('/deal/{deal_id}', include_in_schema=False)
def deal_page(deal_id: str):
    digest(deal_id)
    return FileResponse(ROOT/'static/pilot.html', headers={'Cache-Control':'no-store'})

@router.get('/admin', include_in_schema=False)
def admin_page():
    return FileResponse(ROOT/'static/pilot-admin.html', headers={'Cache-Control':'no-store'})

@router.get('/admin.js', include_in_schema=False)
def admin_script():
    return FileResponse(ROOT/'static/pilot-admin.js', media_type='text/javascript', headers={'Cache-Control':'no-store'})

@router.get('/config')
def config(wallet: str | None = None):
    who = address(wallet) if wallet else None
    result = {'enabled':False, 'chain_id':CHAIN, 'testnet_only':True, 'token':USDC,
              'service_fee_units':0, 'arbiter_fee_units':0, 'capacity':50, 'member':None, 'remaining':None}
    if os.getenv('PILOT_ENABLED','false').lower() != 'true':
        return result
    w,c = connection()
    block = w.eth.block_number
    count = c.functions.memberCount().call(block_identifier=block)
    return {**result, 'enabled':True, 'escrow':c.address, 'treasury':c.functions.treasury().call(block_identifier=block),
            'member_count':count, 'remaining':max(0,50-count), 'observed_block':block,
            'member':c.functions.members(who).call(block_identifier=block) if who else None}

@router.post('/prepare-deployment')
def deployment(req: Deploy):
    owner = address(req.treasury)
    return {'transaction':{'from':address(req.deployer), 'data':ARTIFACT['bytecode']+encode(['address','address'],[USDC,owner]).hex(),
                           'chainId':hex(CHAIN), 'value':'0x0'}, 'treasury':owner, 'testnet_only':True}

class Proposal(BaseModel):
    buyer: str
    seller: str
    arbiter: str
    amount: str
    salt: str
    terms: str = Field(min_length=1, max_length=12000)
    split_bps: int = Field(ge=0,le=10000)
    acceptance_window: int = Field(default=86400, ge=600,le=604800)
    submit_window: int = Field(default=86400, ge=600,le=604800)
    dispute_window: int = Field(default=86400, ge=600,le=604800)
    arbitration_window: int = Field(default=86400, ge=600,le=604800)

def simulated(w,c,caller,fn):
    try:
        fn.call({'from':caller})
    except Exception as e:
        raise HTTPException(409, 'Transaction preflight failed. Check role, balance, approval, state and deadline; refresh the deal.') from e
    return {'transaction':tx(caller,c.address,fn._encode_transaction_data())}

@router.post('/prepare-proposal')
def proposal(req: Proposal):
    buyer,seller,arbiter = map(address,[req.buyer,req.seller,req.arbiter])
    salt,n = digest(req.salt),units(req.amount)
    w,c = connection()
    if len({buyer,seller,arbiter}) != 3 or arbiter == c.functions.treasury().call() or c.address in [buyer,seller,arbiter]:
        raise HTTPException(422,'Buyer, seller and arbitrator must be distinct; arbitrator cannot be admissions wallet.')
    if not c.functions.members(buyer).call():
        raise HTTPException(403,'Buyer has not been admitted to the pilot.')
    key = Web3.keccak(encode(['address','bytes32','string'],[buyer,salt,'AGENTNOTARY_FOUNDING_V1']))
    if c.functions.deals(key).call()[-1] != 0:
        raise HTTPException(409,'Deal already exists. Read its state.')
    h = Web3.keccak(text=req.terms)
    fn = c.functions.proposeDeal(salt,seller,arbiter,n,0,req.split_bps,h,req.acceptance_window,req.submit_window,req.dispute_window,req.arbitration_window)
    approve = Web3.keccak(text='approve(address,uint256)')[:4]+encode(['address','uint256'],[c.address,n])
    return {'deal_id':Web3.to_hex(key),'terms_hash':Web3.to_hex(h),'amount_units':n,'locked_units':n,'fee_units':0,'payout_units':n,
            'fallback_seller_units':n*req.split_bps//10000,'fallback_buyer_units':n-n*req.split_bps//10000,
            'approval':tx(buyer,USDC,Web3.to_hex(approve)), 'proposal':tx(buyer,c.address,fn._encode_transaction_data()),
            'review':req.model_dump(exclude={'salt'}), 'notice':'Save and share the exact terms text with seller and arbitrator. Funds lock when proposal is sent.'}

@router.get('/deals/{deal_id}')
def state(deal_id: str):
    w,c = connection()
    block = w.eth.block_number
    d = c.functions.deals(digest(deal_id)).call(block_identifier=block)
    if not d[-1]:
        raise HTTPException(404,'Deal not found in configured pilot.')
    names=['buyer','seller','arbiter','amount_units','arbiter_fee_units','split_bps','terms_hash','acceptance_deadline',
           'submit_window','dispute_window','arbitration_window','submit_deadline','dispute_deadline','arbitration_deadline',
           'content_hash','seller_accepted','arbiter_accepted','state_index']
    result = dict(zip(names,d))
    for name in ['terms_hash','content_hash']:
        result[name] = Web3.to_hex(result[name])
    payout = d[3] if d[-1] in [5,6] else d[3]*d[5]//10000 if d[-1]==8 else 0
    refund = d[3]-payout if d[-1]>=5 else 0
    return {**result,'deal_id':deal_id,'state':STATES[d[-1]],'observed_block':block,'chain_time':w.eth.get_block(block)['timestamp'],
            'outcome':{'payout_units':payout,'refund_units':refund,'fee_units':0,'locked_units':d[3] if d[-1]<5 else 0},
            'notice':'Latest observed state, not L1 finality. Timeouts require a wallet transaction.'}

class Action(BaseModel):
    caller: str
    action: str
    terms: str = Field(default='',max_length=12000)
    content: str = Field(default='',max_length=12000)
    uri: str = Field(default='',max_length=256)
    reason: str = Field(default='',max_length=12000)

@router.post('/deals/{deal_id}/prepare-action')
def action(deal_id: str, req: Action):
    w,c = connection()
    key,caller = digest(deal_id),address(req.caller)
    simple={'sellerAccept','arbiterAccept','acceptDelivery','finalizeIfSilent','finalizeStalemate','expireProposal','expireUndelivered'}
    if req.action in {'sellerAccept','arbiterAccept'}:
        d = c.functions.deals(key).call()
        if not req.terms or Web3.keccak(text=req.terms) != d[6]:
            raise HTTPException(422,'Exact agreed terms must match the on-chain terms hash before acceptance.')
    if req.action in simple:
        fn=getattr(c.functions,req.action)(key)
    elif req.action=='deliver':
        if not req.content or not req.uri.startswith(('https://','ipfs://')) or len(req.uri.encode('utf-8'))>256:
            raise HTTPException(422,'Supply delivery text and an HTTPS/IPFS URI of at most 256 bytes. Content is hashed, URI is public.')
        fn=c.functions.deliver(key,Web3.keccak(text=req.content),req.uri)
    elif req.action=='disputeDelivery':
        if not req.reason.strip():
            raise HTTPException(422,'A dispute reason is required; share it with the arbitrator separately.')
        fn=c.functions.disputeDelivery(key,Web3.keccak(text=req.reason))
    elif req.action in {'resolveSeller','resolveBuyer'}:
        fn=c.functions.arbitrate(key,req.action=='resolveSeller')
    else:
        raise HTTPException(422,'Unsupported action.')
    return simulated(w,c,caller,fn)

class Admission(BaseModel):
    caller: str
    member: str

@router.post('/prepare-admission')
def admission(req: Admission):
    w,c=connection()
    return simulated(w,c,address(req.caller),c.functions.admitMember(address(req.member)))
