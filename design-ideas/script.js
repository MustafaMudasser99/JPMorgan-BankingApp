const screens = [...document.querySelectorAll('[data-screen]')];
const chatPopup = document.querySelector('[data-chat-popup]');
const chatToggleButtons = [...document.querySelectorAll('[data-chat-toggle]')];

const showScreen = (name) => {
  screens.forEach((screen) => {
    screen.classList.toggle('active', screen.dataset.screen === name);
  });
  const tabButtons = document.querySelectorAll('.tab');
  tabButtons.forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.target === name);
  });
  history.replaceState(null, '', `#${name}`);
};

const toggleChat = () => {
  chatPopup.classList.toggle('open');
};

const handleClick = (event) => {
  const target = event.target.closest('[data-target]');
  if (target) {
    showScreen(target.dataset.target);
    return;
  }
  const chatTarget = event.target.closest('[data-chat-toggle]');
  if (chatTarget) {
    toggleChat();
  }
};

const handleChatSubmit = (event) => {
  const form = event.target.closest('.chat-input');
  if (!form) return;
  event.preventDefault();
  const input = form.querySelector('input');
  if (!input || !input.value.trim()) return;
  const body = chatPopup.querySelector('.chat-body');
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  bubble.textContent = input.value.trim();
  body.appendChild(bubble);
  body.scrollTop = body.scrollHeight;
  input.value = '';
};

const init = () => {
  const initial = location.hash.replace('#', '') || 'login';
  showScreen(initial);
  document.body.addEventListener('click', handleClick);
  document.body.addEventListener('submit', handleChatSubmit);
  window.addEventListener('hashchange', () => {
    const name = location.hash.replace('#', '') || 'login';
    showScreen(name);
  });
};

init();
