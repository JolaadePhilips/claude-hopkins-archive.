(function enhanceSwipeFile(){
  const esc = (value='') => String(value).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));

  function normalise(ad){
    const sourceVolume = ad.sourceVolume ? `Volume ${ad.sourceVolume}` : null;
    const sourcePage = ad.sourcePage ? `page ${ad.sourcePage}` : null;
    const provenance = [sourceVolume, sourcePage].filter(Boolean).join(', ');

    return {
      ...ad,
      context: ad.context || (
        ad.metadataConfidence === 'auto'
          ? `This scan appears in the public Claude Hopkins archive collection. The image provenance is exact${provenance ? ` (${provenance})` : ''}; the brand, date and headline may be OCR-assisted until separately verified.`
          : `A documented Claude Hopkins advertising execution. The notes below separate what can be seen in the ad from what is independently verified about its date and authorship.`
      ),
      whyItWorks: ad.whyItWorks || (
        ad.metadataConfidence === 'auto'
          ? 'This record has not yet received a hand-written analysis. Use the original scan first; detailed swipe-file commentary will be added only after the execution has been checked manually.'
          : [ad.hook, ad.proof].filter(Boolean).join(' ')
      ),
      publication: ad.publication || 'Original publication not yet verified',
      creditLine: ad.creditLine || (
        ad.sourceLabel
          ? `Historical advertisement: ${ad.sourceLabel}. Scan source: CopyLegends / Matt Bockenstette public-domain vault.`
          : `Historical advertisement. Scan source linked below. Additional authorship/date verification sources are listed separately.`
      ),
      sourceStatus: ad.sourceStatus || (
        ad.metadataConfidence === 'auto' ? 'Exact scan provenance; metadata provisional' : 'Hand-verified record'
      )
    };
  }

  window.openDetail = function(ad){
    const a = normalise(ad);
    const year = a.year || 'Date unverified';
    const principles = (a.principles || []).length ? a.principles.join(' · ') : 'Not yet annotated';
    const verificationLinks = (a.verificationSources || []).map(s =>
      `<a class="source-link" href="${esc(s.url)}" target="_blank" rel="noreferrer">↗ ${esc(s.label)}</a>`
    ).join('');

    document.querySelector('#detailInner').innerHTML = `
      <div class="detail-grid">
        <div class="detail-image">
          <img src="${esc(a.image)}" alt="${esc(a.brand)} advertisement: ${esc(a.headline)}">
        </div>
        <div class="detail-copy">
          <div class="meta">${esc(a.brand)} · ${esc(year)} · ${esc(a.product || '')}</div>
          <h2>${esc(a.headline)}</h2>

          <div class="swipe-intro">
            <div class="source-status">${esc(a.sourceStatus)}</div>
            <p>${esc(a.context)}</p>
          </div>

          <div class="fact"><strong>Why it works</strong>${esc(a.whyItWorks)}</div>
          <div class="fact"><strong>Hook</strong>${esc(a.hook || 'Not yet annotated.')}</div>
          <div class="fact"><strong>Offer / CTA</strong>${esc(a.offer || 'Not yet annotated.')}</div>
          <div class="fact"><strong>Proof / mechanism</strong>${esc(a.proof || 'See original scan.')}</div>
          <div class="fact"><strong>Hopkins principles</strong>${esc(principles)}</div>
          <div class="fact"><strong>Original publication</strong>${esc(a.publication)}</div>

          <div class="confidence-row">
            <span class="confidence ${esc(a.attribution || 'low')}">Attribution: ${esc(a.attribution || 'low')}</span>
            <span class="confidence ${esc(a.dateConfidence || 'low')}">Date: ${esc(a.dateConfidence || 'low')}</span>
          </div>

          <div class="credit-box">
            <div class="source-label">Credit / provenance</div>
            <p>${esc(a.creditLine)}</p>
            ${a.sourceVolume ? `<p class="provenance-id">Archive location: volume ${esc(a.sourceVolume)}, page ${esc(a.sourcePage || '')}</p>` : ''}
          </div>

          ${a.note ? `<div class="research-note"><div class="source-label">Research note</div><p>${esc(a.note)}</p></div>` : ''}

          <div class="source-block">
            <div class="source-label">Sources</div>
            ${a.imageSource ? `<a class="source-link" href="${esc(a.imageSource)}" target="_blank" rel="noreferrer">↗ Original scan / archive source</a>` : ''}
            ${verificationLinks}
          </div>
        </div>
      </div>`;
    detail.showModal();
  };
})();
