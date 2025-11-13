// Hamburger Menu Button Component
const HamburgerMenu = ({ onClick, isOpen }) => {
  return (
    <button 
      className={`hamburger ${isOpen ? 'hamburger--open' : ''}`}
      onClick={onClick}
      aria-label="Toggle menu"
    >
      <span></span>
      <span></span>
    </button>
  );
};

