const OnboardingScreen = ({ onComplete }) => {
  const scenes = React.useMemo(
    () => [
      {
        id: 'prep',
        image: '/churchill/angy.png',
        alt: 'Sir Winston Churchill looking serious',
        paragraphs: [
          'If you want me to speak for two minutes, it will take me three weeks of preparation...',
          'If you want me to speak for an hour, I am ready now'
        ],
        autoAdvance: true,
        holdDuration: 2600,
        typingSpeed: 45,
        paragraphPause: 650
      },
      {
        id: 'invite',
        image: '/churchill/hapi.png',
        alt: 'Sir Winston Churchill smiling and raising two fingers',
        paragraphs: [
          'Don’t have weeks to turn your 70-page visual report into a case study?',
          'Try Reframe'
        ],
        hasCta: true,
        typingSpeed: 48,
        paragraphPause: 750
      }
    ],
    []
  );

  const [sceneIndex, setSceneIndex] = React.useState(0);
  const [displayedParagraphs, setDisplayedParagraphs] = React.useState(
    () => scenes[0].paragraphs.map(() => '')
  );
  const [paragraphIndex, setParagraphIndex] = React.useState(0);
  const [charIndex, setCharIndex] = React.useState(0);
  const [isSceneFinished, setIsSceneFinished] = React.useState(false);

  const scene = scenes[sceneIndex];

  React.useEffect(() => {
    setDisplayedParagraphs(scene.paragraphs.map(() => ''));
    setParagraphIndex(0);
    setCharIndex(0);
    setIsSceneFinished(false);
  }, [sceneIndex, scene.paragraphs]);

  React.useEffect(() => {
    const currentScene = scenes[sceneIndex];
    const paragraphs = currentScene.paragraphs;

    if (paragraphIndex >= paragraphs.length) {
      setIsSceneFinished(true);
      return;
    }

    setIsSceneFinished(false);
    const currentParagraph = paragraphs[paragraphIndex];

    if (charIndex < currentParagraph.length) {
      const timeout = setTimeout(() => {
        setDisplayedParagraphs((prev) => {
          const next = [...prev];
          next[paragraphIndex] = currentParagraph.slice(0, charIndex + 1);
          return next;
        });
        setCharIndex((value) => value + 1);
      }, currentScene.typingSpeed || 32);

      return () => clearTimeout(timeout);
    }

    const pauseTimeout = setTimeout(() => {
      setParagraphIndex((value) => value + 1);
      setCharIndex(0);
    }, currentScene.paragraphPause || 600);

    return () => clearTimeout(pauseTimeout);
  }, [charIndex, paragraphIndex, sceneIndex, scenes]);

  React.useEffect(() => {
    const currentScene = scenes[sceneIndex];
    if (!isSceneFinished || !currentScene.autoAdvance) {
      return;
    }

    if (sceneIndex >= scenes.length - 1) {
      return;
    }

    const holdTimeout = setTimeout(() => {
      setSceneIndex((value) => Math.min(value + 1, scenes.length - 1));
    }, currentScene.holdDuration || 2600);

    return () => clearTimeout(holdTimeout);
  }, [isSceneFinished, sceneIndex, scenes]);

  const handleCta = () => {
    if (typeof onComplete === 'function') {
      onComplete();
    }
  };

  const renderLine = (text, idx) => {
    const isActive = paragraphIndex === idx && !isSceneFinished;
    const showCaret =
      isActive &&
      charIndex < (scene.paragraphs[idx]?.length || 0) &&
      !(scene.hasCta && idx === scene.paragraphs.length - 1);

    if (scene.hasCta && idx === scene.paragraphs.length - 1) {
      const isCtaActive = text.length > 0 || isSceneFinished;
      return (
        <button
          key={`${scene.id}-${idx}`}
          className={`onboarding-link ${isSceneFinished ? 'onboarding-link--ready' : ''}`}
          onClick={handleCta}
          disabled={!isSceneFinished}
          type="button"
        >
          <span className="onboarding-link__label">
            {isCtaActive ? (
              <>
                {text}
                <span aria-hidden="true" className="onboarding-link__arrow">→</span>
              </>
            ) : (
              ''
            )}
          </span>
          <span className="sr-only">Go to upload screen</span>
        </button>
      );
    }

    return (
      <p
        key={`${scene.id}-${idx}`}
        className="type-line"
      >
        {text}
        {showCaret && <span className="type-caret" aria-hidden="true" />}
      </p>
    );
  };

  return (
    <div className="onboarding-screen">
      <div key={scene.id} className="onboarding-frame onboarding-frame--animated">
        <div className="onboarding-image-wrap">
          <img src={scene.image} alt={scene.alt} className="onboarding-image" />
        </div>
        <div className="onboarding-text">
          {displayedParagraphs.map((line, idx) => renderLine(line, idx))}
        </div>
      </div>
    </div>
  );
};


