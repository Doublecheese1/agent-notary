const fs = require('fs'), path = require('path');
const solc = require('solc');
const root = path.resolve(__dirname, '..');
const sources = Object.fromEntries(['AgentNotaryEscrow.sol','TestUSDC.sol'].map(name => [name,{content:fs.readFileSync(path.join(root,'contracts',name),'utf8')} ]));
const output = JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,settings:{evmVersion:'paris',optimizer:{enabled:true,runs:200},outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}}),{import: name=>({contents:fs.readFileSync(require.resolve(name),'utf8')})}));
for(const error of output.errors || []) { if(error.severity === 'error') throw new Error(error.formattedMessage); }
fs.mkdirSync(path.join(root,'artifacts'),{recursive:true});
for(const name of ['AgentNotaryEscrow','TestUSDC']) {
 const c = output.contracts[name+'.sol'][name];
 fs.writeFileSync(path.join(root,'artifacts',name+'.json'),JSON.stringify({compiler:solc.version(),abi:c.abi,bytecode:'0x'+c.evm.bytecode.object},null,2));
}
console.log('Compiled escrow and local test token.');
