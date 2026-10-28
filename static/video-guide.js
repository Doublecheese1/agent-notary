(() => {
  const video = document.getElementById('explainerVideo');
  const title = document.getElementById('videoChapterTitle');
  const description = document.getElementById('videoChapterDescription');
  const buttons = Array.from(document.querySelectorAll('[data-video-chapter]'));
  if (!video || !title || !description || buttons.length !== 5) return;
  const params = new URLSearchParams(location.search);
  const language = ['en', 'tr', 'es', 'pt-br', 'ru', 'zh-cn'].includes((params.get('lang') || '').toLowerCase())
    ? params.get('lang').toLowerCase() : 'en';
  const tracks = Array.from(video.querySelectorAll('track[kind="subtitles"]'));

  function showLanguage() {
    Array.from(video.textTracks).forEach((track) => {
      track.mode = track.language.toLowerCase() === language ? 'showing' : 'disabled';
    });
  }

  const chapters = {
    '01': {
      title: 'How AgentSolis works',
      description: 'Agree on the outcome and evidence, lock USDC, deliver the work, then settle by the agreed rules.',
      file: '01-overview.mp4',
    },
    '02': {
      title: 'Connect your wallet',
      description: 'Choose your wallet and check Arbitrum One and your address. Connecting alone does not move USDC.',
      file: '02-wallet.mp4',
    },
    '03': {
      title: 'Buyer: create and fund',
      description: 'Review the result, evidence and budget. USDC approval and locking the budget are separate steps.',
      file: '03-buyer.mp4',
    },
    '04': {
      title: 'Seller: review and deliver',
      description: 'Review the terms, accept the seller role and submit the agreed work and evidence for review.',
      file: '04-seller.mp4',
    },
    '05': {
      title: 'Founding 50',
      description: 'Approved buyer and seller participants can qualify for 30 days without an AgentSolis protocol fee from their first funded deal. Job amount and network costs still apply.',
      file: '05-founding50.mp4',
    },
  };

  function selectChapter(id) {
    const chapter = chapters[id];
    if (!chapter) return;
    video.pause();
    video.setAttribute('poster', `/assets/videos/${id}-poster.png`);
    video.setAttribute('src', `/assets/videos/${chapter.file}?v=20261028c`);
    tracks.forEach((track) => track.setAttribute('src', `/assets/videos/${id}.${track.srclang.toLowerCase()}.vtt`));
    video.setAttribute('aria-label', `${chapter.title}, 30-second illustrative video in English`);
    video.load();
    showLanguage();
    title.textContent = chapter.title;
    description.textContent = chapter.description;
    buttons.forEach((button) => button.setAttribute('aria-pressed', button.dataset.videoChapter === id ? 'true' : 'false'));
  }

  buttons.forEach((button) => button.addEventListener('click', () => selectChapter(button.dataset.videoChapter)));
  video.addEventListener('loadedmetadata', showLanguage);
  const requested = params.get('video');
  if (requested && chapters[requested]) selectChapter(requested);
  else showLanguage();
})();
