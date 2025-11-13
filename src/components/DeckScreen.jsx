// Deck Screen Component
const DeckScreen = ({ slideDeck, pdfTitle }) => {
  React.useEffect(() => {
    if (slideDeck && window.deckUtils && window.deckUtils.renderSlideDeck) {
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        window.deckUtils.renderSlideDeck(slideDeck);
      }, 50);
    }
  }, [slideDeck]);

  return (
    <div id="deck-screen">
      <header className="topbar">
        <div className="crumb">
          <span className="crumb__title">{pdfTitle || 'Deck'}</span>
          <span className="crumb__sep">/</span>
          <span className="crumb__meta" id="deck-meta">10 slides</span>
        </div>
        <div className="actions">
          <div className="export-dropdown">
            <button className="btn btn--ghost" id="export-btn">Export</button>
            <div className="dropdown-menu" id="export-menu">
              <button className="dropdown-item" data-format="png">Export as PNG</button>
              <button className="dropdown-item" data-format="svg">Export as SVG</button>
            </div>
          </div>
        </div>
      </header>

      <main className="deck" id="deck">
        {/* Slides will be rendered here */}
      </main>

      <footer className="bottom-toolbar">
        <div className="toolbar-group">
          <div className="background-dropdown">
            <button className="toolbar-btn" id="background-btn">
              <span>Background</span>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <div className="toolbar-dropdown-menu" id="background-menu">
              <button className="toolbar-dropdown-item" data-theme="light">Light Mode</button>
              <button className="toolbar-dropdown-item" data-theme="dark">Dark Mode</button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

