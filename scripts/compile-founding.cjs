const fs = require('fs'), path = require('path');
const solc = require('solc');
const root = path.resolve(__dirname, '..');

const sources = {
  'AgentNotaryFoundingEscrow.sol': {
    content: fs.readFileSync(path.join(root, 'contracts', 'AgentNotaryFoundingEscrow.sol'), 'utf8')
  }
};

const output = JSON.parse(solc.compile(JSON.stringify({
  language: 'Solidity',
  sources,
  settings: {
    evmVersion: 'paris',
    optimizer: { enabled: true, runs: 200 },
    viaIR: true,
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } }
  }
}), { import: name => ({ contents: fs.readFileSync(require.resolve(name), 'utf8') }) }));

for (const error of output.errors || []) {
  if (error.severity === 'error') throw new Error(error.formattedMessage);
}

fs.mkdirSync(path.join(root, 'artifacts'), { recursive: true });
const c = output.contracts['AgentNotaryFoundingEscrow.sol']['AgentNotaryFoundingEscrow'];
fs.writeFileSync(
  path.join(root, 'artifacts', 'AgentNotaryFoundingEscrow.json'),
  JSON.stringify({ compiler: solc.version(), abi: c.abi, bytecode: '0x' + c.evm.bytecode.object }, null, 2)
);
console.log('Compiled AgentNotaryFoundingEscrow.sol with viaIR=true. Legacy compile.cjs and its artifacts were not touched.');
