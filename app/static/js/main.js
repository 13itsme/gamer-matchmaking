function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]').content;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text == null ? '' : String(text)));
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      flash.style.opacity = '0';
      flash.style.transform = 'translateX(120%)';
      setTimeout(() => flash.remove(), 400);
    }, 5000);
  });
});

