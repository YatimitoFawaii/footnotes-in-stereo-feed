const input = document.querySelector('#episode-search');
const cards = [...document.querySelectorAll('.episode-card')];
const empty = document.querySelector('#empty-state');

input?.addEventListener('input', () => {
  const query = input.value.trim().toLowerCase();
  let visible = 0;
  cards.forEach((card) => {
    const match = !query || card.textContent.toLowerCase().includes(query);
    card.hidden = !match;
    visible += Number(match);
  });
  empty.hidden = visible !== 0;
});
