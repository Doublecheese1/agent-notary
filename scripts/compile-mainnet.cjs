const fs = require('fs');
const path = require('path');
const solc = require('solc');
const root = path.resolve(__dirname, '..');

const sources = {};
for (const name of ['AgentNotaryMainnetEscrow.sol', 'AgentNotaryValidatorQuorum.sol', 'AgentNotaryAIReviewResolver.sol', 'TestUSDC.sol']) {
  sources[name] = { content: fs.readFileSync(path.join(root, 'contracts', name), 'utf8') };
}

const output = JSON.parse(solc.compile(JSON.stringify({
  language: 'Solidity',
  sources,
  settings: {
    evmVersion: 'cancun',
    optimizer: { enabled: true, runs: 500 },
    viaIR: true,
    outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object', 'metadata'] } }
  }
}), { import: name => ({ contents: fs.readFileSync(require.resolve(name), 'utf8') }) }));

for (const error of output.errors || []) {
  const line = error.formattedMessage || error.message;
  if (error.severity === 'error') throw new Error(line);
  process.stderr.write(line + '\n');
}

fs.mkdirSync(path.join(root, 'artifacts'), { recursive: true });
for (const name of ['AgentNotaryMainnetEscrow', 'AgentNotaryValidatorQuorum', 'AgentNotaryAIReviewResolver', 'TestUSDC']) {
  const contract = output.contracts[`${name}.sol`][name];
  fs.writeFileSync(path.join(root, 'artifacts', `${name}.json`), JSON.stringify({
    compiler: solc.version(),
    abi: contract.abi,
    bytecode: `0x${contract.evm.bytecode.object}`,
    deployedBytecode: `0x${contract.evm.deployedBytecode.object}`,
    metadata: JSON.parse(contract.metadata)
  }, null, 2));
}
console.log(`Compiled mainnet candidate with ${solc.version()}. This does not deploy it.`);
