// hamburger menu button component
const HamburgerMenu = ({ onClick, isOpen }) => {
  return (
    <button 
      className={`hamburger ${isOpen ? 'hamburger--open' : ''}`}
      onClick={onClick}
      aria-label="Toggle menu"
    >
      {/* two lines that animate into an X when open */}
      <span></span>
      <span></span>
    </button>
  );
};

