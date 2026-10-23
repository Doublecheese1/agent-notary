const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const root = path.resolve(__dirname, '..');
const release = JSON.parse(fs.readFileSync(path.join(root, 'release', 'mainnet-release.json'), 'utf8'));
const solcPath = process.env.SOLC_MODULE_PATH || 'solc';
const solc = require(solcPath);
const openZeppelinRoot = process.env.OPENZEPPELIN_CONTRACTS_ROOT
  ? path.resolve(process.env.OPENZEPPELIN_CONTRACTS_ROOT)
  : path.join(root, 'node_modules', '@openzeppelin', 'contracts');

const deployments = [
  {
    key: 'validator_quorum',
    source: 'AgentNotaryValidatorQuorum.sol',
    contract: 'AgentNotaryValidatorQuorum',
    artifact: 'AgentNotaryValidatorQuorum.json'
  },
  {
    key: 'ai_review_resolver',
    source: 'AgentNotaryAIReviewResolver.sol',
    contract: 'AgentNotaryAIReviewResolver',
    artifact: 'AgentNotaryAIReviewResolver.json'
  },
  {
    key: 'escrow',
    source: 'AgentNotaryMainnetEscrow.sol',
    contract: 'AgentNotaryMainnetEscrow',
    artifact: 'AgentNotaryMainnetEscrow.json'
  }
].map(item => ({ ...item, ...release.deployed_contracts[item.key] }));

function lf(file) {
  return fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
}

function sourceContent(name) {
  if (name.startsWith('@openzeppelin/contracts/')) {
    const relative = name.slice('@openzeppelin/contracts/'.length);
    return lf(path.join(openZeppelinRoot, relative));
  }
  return lf(path.join(root, 'contracts', name));
}

const sourceNames = new Set([
  'AgentNotaryMainnetEscrow.sol',
  'AgentNotaryValidatorQuorum.sol',
  'AgentNotaryAIReviewResolver.sol'
]);
for (const deployment of deployments) {
  const artifact = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', deployment.artifact), 'utf8'));
  for (const name of Object.keys(artifact.metadata.sources || {})) sourceNames.add(name);
}
const sources = Object.fromEntries([...sourceNames].sort().map(name => [name, { content: sourceContent(name) }]));
const settings = {
  evmVersion: 'cancun',
  optimizer: { enabled: true, runs: 500 },
  viaIR: true,
  outputSelection: {
    '*': {
      '*': [
        'abi',
        'metadata',
        'evm.bytecode.object',
        'evm.bytecode.linkReferences',
        'evm.deployedBytecode.object',
        'evm.deployedBytecode.immutableReferences',
        'evm.deployedBytecode.linkReferences'
      ]
    }
  }
};
const standardInput = { language: 'Solidity', sources, settings };
const compiled = JSON.parse(solc.compile(JSON.stringify(standardInput)));
for (const error of compiled.errors || []) {
  if (error.severity === 'error') throw new Error(error.formattedMessage || error.message);
}

async function rpcBatch() {
  const requests = [];
  let id = 1;
  for (const deployment of deployments) {
    requests.push({ jsonrpc: '2.0', id: id++, method: 'eth_getTransactionByHash', params: [deployment.transaction] });
    requests.push({ jsonrpc: '2.0', id: id++, method: 'eth_getTransactionReceipt', params: [deployment.transaction] });
    requests.push({ jsonrpc: '2.0', id: id++, method: 'eth_getCode', params: [deployment.address, 'latest'] });
  }
  let body;
  if (process.env.ARBITRUM_RPC_RESPONSE_FILE) {
    body = JSON.parse(fs.readFileSync(path.resolve(process.env.ARBITRUM_RPC_RESPONSE_FILE), 'utf8'));
  } else {
    const url = process.env.ARBITRUM_RPC_URL || 'https://arb1.arbitrum.io/rpc';
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(requests)
    });
    if (!response.ok) throw new Error(`Arbitrum RPC returned HTTP ${response.status}`);
    body = await response.json();
  }
  const byId = new Map(body.map(item => [item.id, item]));
  return deployments.map((deployment, index) => {
    const base = index * 3 + 1;
    for (const current of [byId.get(base), byId.get(base + 1), byId.get(base + 2)]) {
      if (!current || current.error) throw new Error(`Arbitrum RPC failed for ${deployment.key}`);
    }
    return { transaction: byId.get(base).result, receipt: byId.get(base + 1).result, code: byId.get(base + 2).result };
  });
}

function maskImmutables(hex, refs) {
  const buffer = Buffer.from(hex.replace(/^0x/, ''), 'hex');
  for (const positions of Object.values(refs || {})) {
    for (const { start, length } of positions) buffer.fill(0, start, start + length);
  }
  return buffer.toString('hex');
}

function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

(async () => {
  const chain = await rpcBatch();
  const outputRoot = path.join(root, 'release', 'arbiscan-verification');
  fs.rmSync(outputRoot, { recursive: true, force: true });
  fs.mkdirSync(outputRoot, { recursive: true });
  const results = [];

  deployments.forEach((deployment, index) => {
    const artifact = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', deployment.artifact), 'utf8'));
    const built = compiled.contracts[deployment.source][deployment.contract];
    const { transaction, receipt, code } = chain[index];
    const expectedCreation = `0x${built.evm.bytecode.object}`.toLowerCase();
    const artifactCreation = artifact.bytecode.toLowerCase();
    const input = (transaction.input || '').toLowerCase();
    const constructorArguments = input.startsWith(expectedCreation) ? input.slice(expectedCreation.length) : null;
    const compiledRuntime = maskImmutables(built.evm.deployedBytecode.object, built.evm.deployedBytecode.immutableReferences);
    const onchainRuntime = maskImmutables(code, built.evm.deployedBytecode.immutableReferences);
    const checks = {
      compiler_matches_artifact: artifact.compiler === solc.version(),
      compiled_creation_matches_artifact: expectedCreation === artifactCreation,
      transaction_creation_prefix_matches: constructorArguments !== null,
      receipt_succeeded: receipt && receipt.status === '0x1',
      receipt_address_matches: receipt && receipt.contractAddress && receipt.contractAddress.toLowerCase() === deployment.address.toLowerCase(),
      onchain_runtime_matches_ignoring_immutables: compiledRuntime === onchainRuntime
    };
    const directory = path.join(outputRoot, deployment.key);
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, 'standard-input.json'), JSON.stringify(standardInput, null, 2));
    fs.writeFileSync(path.join(directory, 'constructor-arguments.txt'), `${constructorArguments || ''}\n`);
    const record = {
      network: release.network,
      chain_id: release.chain_id,
      address: deployment.address,
      deployment_transaction: deployment.transaction,
      compiler: `v${solc.version().replace('.Emscripten.clang', '')}`,
      contract_name: `${deployment.source}:${deployment.contract}`,
      optimization: { enabled: true, runs: 500 },
      evm_version: 'cancun',
      via_ir: true,
      constructor_arguments_without_0x: constructorArguments,
      standard_input_sha256: sha256(JSON.stringify(standardInput)),
      checks,
      ready_for_submission: Object.values(checks).every(Boolean)
    };
    fs.writeFileSync(path.join(directory, 'verification.json'), JSON.stringify(record, null, 2));
    results.push({ key: deployment.key, ...record });
  });

  const report = {
    generated_at: new Date().toISOString(),
    note: 'This package proves local source/bytecode consistency. Arbiscan verification is complete only after the explorer reports a verified source.',
    all_checks_pass: results.every(item => item.ready_for_submission),
    contracts: results
  };
  fs.writeFileSync(path.join(outputRoot, 'verification-report.json'), JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(outputRoot, 'README.md'), [
    '# AgentSolis Arbiscan verification package',
    '',
    'Use Solidity Standard JSON Input on Arbiscan for each contract directory.',
    'Select the compiler and contract name recorded in `verification.json`, then paste the constructor arguments from `constructor-arguments.txt`.',
    'All local checks must be true before submission. An API key or an interactive Arbiscan submission is still required.',
    ''
  ].join('\n'));
  console.log(JSON.stringify({ output: outputRoot, all_checks_pass: report.all_checks_pass, contracts: results.map(item => ({ key: item.key, ready: item.ready_for_submission, checks: item.checks })) }, null, 2));
})().catch(error => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
