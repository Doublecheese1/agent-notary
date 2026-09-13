// Separate compile entrypoint for AgentNotaryOpenEscrow.sol ONLY.
// Does NOT touch scripts/compile.cjs and does NOT recompile AgentNotaryEscrow.sol
// or TestUSDC.sol — those artifacts (artifacts/AgentNotaryEscrow.json,
// artifacts/TestUSDC.json) are left exactly as the existing `npm run compile`
// produces them. Run this with `node scripts/compile-open.cjs` after the
// existing `npm run compile` has already produced artifacts/TestUSDC.json
// (the open-escrow test suite reuses that existing TestUSDC artifact for
// deployment; it does not need its own copy).
//
// viaIR is required here (and only here): AgentNotaryOpenEscrow.sol hit a
// "Stack too deep" error under the legacy settings (evmVersion=paris,
// optimizer runs=200, no viaIR) that AgentNotaryEscrow.sol compiles fine
// under. Confirmed locally by the project owner, not independently
// reproduced in this environment (no solc/npm available here).
const fs = require('fs'), path = require('path');
const solc = require('solc');
const root = path.resolve(__dirname, '..');

const sources = {
  'AgentNotaryOpenEscrow.sol': {
    content: fs.readFileSync(path.join(root, 'contracts', 'AgentNotaryOpenEscrow.sol'), 'utf8')
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
const c = output.contracts['AgentNotaryOpenEscrow.sol']['AgentNotaryOpenEscrow'];
fs.writeFileSync(
  path.join(root, 'artifacts', 'AgentNotaryOpenEscrow.json'),
  JSON.stringify({ compiler: solc.version(), abi: c.abi, bytecode: '0x' + c.evm.bytecode.object }, null, 2)
);
console.log('Compiled AgentNotaryOpenEscrow.sol with viaIR=true. Legacy compile.cjs and its artifacts were not touched.');
