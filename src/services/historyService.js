// LocalStorage service for case study history
const HistoryService = {
  getHistory: () => {
    try {
      const history = localStorage.getItem('caseStudyHistory');
      return history ? JSON.parse(history) : [];
    } catch (e) {
      return [];
    }
  },
  
  addToHistory: (caseStudy) => {
    try {
      const history = HistoryService.getHistory();
      // Remove if already exists (to move to top)
      const filtered = history.filter(h => h.id !== caseStudy.id);
      // Add to beginning
      const updated = [caseStudy, ...filtered].slice(0, 50); // Keep last 50
      localStorage.setItem('caseStudyHistory', JSON.stringify(updated));
    } catch (e) {
      console.error('Failed to save to history:', e);
    }
  },
  
  getCaseStudy: (id) => {
    const history = HistoryService.getHistory();
    return history.find(h => h.id === id);
  }
};

// Export for use in React
if (typeof window !== 'undefined') {
  window.HistoryService = HistoryService;
}

