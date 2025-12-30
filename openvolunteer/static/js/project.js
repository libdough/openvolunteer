import '../sass/project.scss';

/* Project specific Javascript goes here. */

/* Copy Component */
document.addEventListener('click', function (e) {
  const btn = e.target.closest('.copy-btn');
  if (!btn) return;

  const block = btn.closest('.copy-block');
  if (!block) return;

  const content = block.querySelector('.copy-content');
  if (!content) return;

  navigator.clipboard.writeText(content.innerText).then(() => {
    const original = btn.innerText;
    btn.innerText = 'Copied';
    btn.disabled = true;

    setTimeout(() => {
      btn.innerText = original;
      btn.disabled = false;
    }, 1500);
  });
});
