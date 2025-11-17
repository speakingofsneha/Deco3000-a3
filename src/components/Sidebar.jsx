// sidebar component with navigation and history
const Sidebar = ({ isOpen, onClose, onNavigate, currentScreen }) => {
  const [history, setHistory] = React.useState([]);

  // load history when sidebar opens
  React.useEffect(() => {
    if (window.HistoryService) {
      setHistory(window.HistoryService.getHistory());
    }
  }, [isOpen]);

  // navigate to upload screen
  const handleHomeClick = () => {
    onNavigate('upload');
    onClose();
  };

  // navigate to deck screen with selected case study
  const handleHistoryClick = (caseStudy) => {
    onNavigate('deck', { caseStudy });
    onClose();
  };

  // delete a case study from history
  const handleDelete = (e, caseStudyId) => {
    e.preventDefault();
    e.stopPropagation(); // prevent triggering the history item click
    
    // double check before deleting
    const confirmed = window.confirm('Are you sure you want to delete this case study?');
    if (confirmed) {
      if (window.HistoryService) {
        const success = window.HistoryService.deleteFromHistory(caseStudyId);
        if (success) {
          // refresh history list
          const updatedHistory = window.HistoryService.getHistory();
          setHistory(updatedHistory);
        } else {
          console.error('Failed to delete case study');
          alert('Failed to delete case study. Please try again.');
        }
      } else {
        console.error('HistoryService not available');
        alert('History service not available. Please refresh the page.');
      }
    }
  };

  const isDeckScreen = currentScreen === 'deck';
  
  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''} ${isDeckScreen ? 'sidebar--deck' : ''}`}>
      <div className="sidebar__header">
        {/* close button only shows on deck screen */}
        {isDeckScreen && (
          <button 
            className="sidebar__close"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
      </div>
        
        {/* navigation to new document */}
        <nav className="sidebar__nav">
          <button 
            className={`sidebar__nav-item ${currentScreen === 'upload' ? 'sidebar__nav-item--active' : ''}`}
            onClick={handleHomeClick}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 6V14M6 10H14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>New Document</span>
          </button>
        </nav>
        
        {/* history section with list of case studies */}
        <div className="sidebar__section">
          <h3 className="sidebar__section-title">History</h3>
          <div className="sidebar__history">
            {history.length === 0 ? (
              <p className="sidebar__empty">No case studies yet</p>
            ) : (
              history.map((item) => (
                <div
                  key={item.id}
                  className="sidebar__history-item-wrapper"
                >
                  {/* clickable history item */}
                  <button
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
                  {/* delete button for each item */}
                  <button
                    className="sidebar__history-delete"
                    onClick={(e) => handleDelete(e, item.id)}
                    onMouseDown={(e) => e.stopPropagation()} // prevent event bubbling
                    aria-label="Delete case study"
                    type="button"
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
  );
};

