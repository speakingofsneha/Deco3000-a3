const { useState, useEffect, useCallback, useRef } = React;

// API base URL
const API_BASE_URL = '';

// Main App Component
const App = () => {
  // Check if onboarding has been shown in this session
  const hasSeenOnboarding = sessionStorage.getItem('onboardingShown') === 'true';
  const [screen, setScreen] = useState(hasSeenOnboarding ? 'upload' : 'onboarding');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [loadingTitle, setLoadingTitle] = useState('Generating outline');
  const progressIntervalRef = useRef(null);
  const caseStudySectionsRef = useRef({
    currentIndex: 0,
    total: 8
  });
  
  // State for file processing
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFilePath, setUploadedFilePath] = useState(null);
  const [currentOutline, setCurrentOutline] = useState(null);
  const [currentBulletsData, setCurrentBulletsData] = useState(null);
  const [currentPdfPath, setCurrentPdfPath] = useState(null);
  const [currentNarrative, setCurrentNarrative] = useState(null);
  const [slideDeck, setSlideDeck] = useState(null);
  const [pdfTitle, setPdfTitle] = useState('');
  
  const navigate = useCallback((newScreen, data = {}) => {
    setScreen(newScreen);
    if (data.caseStudy) {
      loadCaseStudyFromHistory(data.caseStudy);
    }
  }, []);
  
  const handleOnboardingComplete = useCallback(() => {
    // Mark onboarding as shown in this session
    sessionStorage.setItem('onboardingShown', 'true');
    setScreen('upload');
  }, []);

  const loadCaseStudyFromHistory = async (caseStudy) => {
    setLoading(true);
    setLoadingTitle('Loading case study');
    setLoadingMessage('Retrieving saved slides...');
    try {
      setSlideDeck(caseStudy.slideDeck);
      setPdfTitle(caseStudy.title);
      setLoading(false);
      setScreen('deck');
      // DeckScreen useEffect will handle rendering
    } catch (error) {
      console.error('Failed to load case study:', error);
      setLoading(false);
    }
  };

  const handleFileSelected = (file) => {
    setSelectedFile(file);
  };

  const handleReframe = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setLoadingTitle('Generating outline');
    setLoadingMessage('');
    setScreen('loading');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData
      });

      if (!uploadResponse.ok) {
        const error = await uploadResponse.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const uploadData = await uploadResponse.json();
      setUploadedFilePath(uploadData.file_path);

      setLoadingTitle('Generating outline');
      setLoadingMessage('');
      const outlineFormData = new FormData();
      outlineFormData.append('pdf_path', uploadData.file_path);
      outlineFormData.append('max_chunks', '1000');
      outlineFormData.append('chunk_size', '500');
      outlineFormData.append('overlap', '50');

      const outlineResponse = await fetch(`${API_BASE_URL}/generate-outline`, {
        method: 'POST',
        body: outlineFormData
      });

      if (!outlineResponse.ok) {
        const error = await outlineResponse.json();
        throw new Error(error.detail || 'Outline generation failed');
      }

      const outlineData = await outlineResponse.json();

      if (!outlineData.success || !outlineData.outline || !outlineData.narrative_plan) {
        throw new Error(outlineData.message || 'Invalid response');
      }

      setCurrentOutline(outlineData.outline);
      setCurrentPdfPath(uploadData.file_path);
      setCurrentNarrative(outlineData.narrative_plan);
      setScreen('edit');

    } catch (error) {
      console.error('Error:', error);
      alert(error.message || 'An error occurred. Please try again.');
      setScreen('upload');
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = async (narrative) => {
    if (!currentOutline || !currentPdfPath) return;

    setLoading(true);
    startCaseStudyProgress();
    setScreen('loading');

    try {
      const regenerateRequest = {
        pdf_path: currentPdfPath,
        outline: currentOutline,
        narrative,
        max_chunks: 1000,
        chunk_size: 500,
        overlap: 50
      };

      const regenerateResponse = await fetch(`${API_BASE_URL}/regenerate-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(regenerateRequest)
      });

      if (!regenerateResponse.ok) {
        const error = await regenerateResponse.json();
        throw new Error(error.detail || 'Narrative processing failed');
      }

      const regenerateData = await regenerateResponse.json();

      if (!regenerateData.success) {
        throw new Error(regenerateData.message || 'Narrative processing failed');
      }

      setCurrentOutline(regenerateData.outline);
      setCurrentBulletsData(regenerateData.bullets_data);
      setCurrentNarrative(narrative);

      stopCaseStudyProgress();
      setLoadingTitle('Generating slide deck');
      setLoadingMessage('');

      const formData = new FormData();
      formData.append('pdf_path', currentPdfPath);
      formData.append('outline', JSON.stringify(regenerateData.outline));
      formData.append('bullets_data', JSON.stringify(regenerateData.bullets_data));

      const response = await fetch(`${API_BASE_URL}/generate-slides`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Slide generation failed');
      }

      const data = await response.json();

      if (!data.success || !data.slide_deck) {
        throw new Error(data.message || 'Slide generation failed');
      }

      // Save to history
      const caseStudy = {
        id: Date.now().toString(),
        title: window.deckUtils ? window.deckUtils.extractPdfName(data.slide_deck.source_pdf) : 'slides',
        createdAt: new Date().toISOString(),
        slideDeck: data.slide_deck,
        pdfPath: currentPdfPath
      };
      
      if (window.HistoryService) {
        window.HistoryService.addToHistory(caseStudy);
      }

      setSlideDeck(data.slide_deck);
      setPdfTitle(caseStudy.title);
      setLoading(false);
      setScreen('deck');
      // DeckScreen useEffect will handle rendering

    } catch (error) {
      stopCaseStudyProgress();
      console.error('Error:', error);
      alert(error.message || 'Failed to generate slides');
      setScreen('edit');
      setLoading(false);
    }
  };

  const startCaseStudyProgress = () => {
    stopCaseStudyProgress();
    const totalSections = 8;
    caseStudySectionsRef.current = { currentIndex: 0, total: totalSections };
    setLoadingTitle(`0/${totalSections} sections generated`);
    setLoadingMessage('');
    
    progressIntervalRef.current = setInterval(() => {
      caseStudySectionsRef.current.currentIndex = Math.min(
        caseStudySectionsRef.current.currentIndex + 1,
        totalSections
      );
      setLoadingTitle(`${caseStudySectionsRef.current.currentIndex}/${totalSections} sections generated`);
    }, 1200);
  };

  const stopCaseStudyProgress = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  };

  const isOnboarding = screen === 'onboarding';

  return (
    <>
      {!isOnboarding && screen !== 'deck' && (
        <>
          <HamburgerMenu 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            isOpen={sidebarOpen}
          />
          
          <Sidebar 
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onNavigate={navigate}
            currentScreen={screen}
          />
        </>
      )}
      
      {!isOnboarding && screen === 'deck' && (
        <Sidebar 
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNavigate={navigate}
          currentScreen={screen}
        />
      )}

      {loading && <LoadingScreen title={loadingTitle} message={loadingMessage} />}

      {!loading && isOnboarding && (
        <OnboardingScreen onComplete={handleOnboardingComplete} />
      )}
      
      {!loading && screen === 'upload' && (
        <UploadScreen 
          onFileSelected={handleFileSelected}
          onReframe={handleReframe}
        />
      )}
      
      {!loading && screen === 'edit' && (
        <EditScreen 
          narrative={currentNarrative}
          onContinue={handleContinue}
        />
      )}
      
      {!loading && screen === 'deck' && (
        <DeckScreen
          slideDeck={slideDeck}
          pdfTitle={pdfTitle}
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
          isMenuOpen={sidebarOpen}
        />
      )}
    </>
  );
};

// Render the app
ReactDOM.render(<App />, document.getElementById('root'));

