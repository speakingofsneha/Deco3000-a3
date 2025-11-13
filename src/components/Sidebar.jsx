// Sidebar Component
const Sidebar = ({ isOpen, onClose, onNavigate, currentScreen }) => {
  const [history, setHistory] = React.useState([]);

  React.useEffect(() => {
    if (window.HistoryService) {
      setHistory(window.HistoryService.getHistory());
    }
  }, [isOpen]);

  const handleHomeClick = () => {
    onNavigate('upload');
    onClose();
  };

  const handleHistoryClick = (caseStudy) => {
    onNavigate('deck', { caseStudy });
    onClose();
  };

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
      <div className="sidebar__header">
      </div>
        
        <nav className="sidebar__nav">
          <button 
            className={`sidebar__nav-item ${currentScreen === 'upload' ? 'sidebar__nav-item--active' : ''}`}
            onClick={handleHomeClick}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 10L9 4M3 10L9 16M3 10H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>New Document</span>
          </button>
        </nav>
        
        <div className="sidebar__section">
          <h3 className="sidebar__section-title">History</h3>
          <div className="sidebar__history">
            {history.length === 0 ? (
              <p className="sidebar__empty">No case studies yet</p>
            ) : (
              history.map((item) => (
                <button
                  key={item.id}
                  className="sidebar__history-item"
                  onClick={() => handleHistoryClick(item)}
                >
                  <div className="sidebar__history-content">
                    <span className="sidebar__history-title">{item.title}</span>
                    <span className="sidebar__history-date">
                      {new Date(item.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </aside>
  );
};

