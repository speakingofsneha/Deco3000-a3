// deck screen component
const DeckScreen = ({ slideDeck, pdfTitle, onMenuClick, isMenuOpen }) => {
  // render the slide deck when it changes, need a tiny delay so the dom is ready
  React.useEffect(() => {
    // check if deckUtils is available before trying to render
    if (slideDeck && window.deckUtils && window.deckUtils.renderSlideDeck) {
      setTimeout(() => {
        window.deckUtils.renderSlideDeck(slideDeck);
      }, 50);
    }
  }, [slideDeck]);

  return (
    <div id="deck-screen">
      {/* top bar with menu button, title, and export options */}
      <header className="topbar">
        <div className="crumb">
          {/* hamburger menu button, changes class when open */}
          <button 
            className={`hamburger hamburger--crumb ${isMenuOpen ? 'hamburger--open' : ''}`}
            onClick={onMenuClick}
            aria-label="Toggle menu"
          >
            <span></span>
            <span></span>
          </button>
          {/* show pdf title or default to 'Deck' */}
          <span className="crumb__title">{pdfTitle || 'Deck'}</span>
          <span className="crumb__sep">/</span>
          <span className="crumb__meta" id="deck-meta">10 slides</span>
        </div>
        <div className="actions">
          {/* export dropdown for png and svg */}
          <div className="export-dropdown">
            <button className="btn btn--ghost" id="export-btn">Export</button>
            <div className="dropdown-menu" id="export-menu">
              <button className="dropdown-item" data-format="png">Export as PNG</button>
              <button className="dropdown-item" data-format="svg">Export as SVG</button>
            </div>
          </div>
        </div>
      </header>

      {/* main deck area where slides get rendered */}
      <main className="deck" id="deck">
        {/* slides will be rendered here */}
      </main>

      {/* bottom toolbar with background theme options */}
      <footer className="bottom-toolbar">
        <div className="toolbar-group">
          <div className="background-dropdown">
            {/* background theme switcher button with dropdown arrow */}
            <button className="toolbar-btn" id="background-btn">
              <span>Background</span>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            {/* theme options menu */}
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

