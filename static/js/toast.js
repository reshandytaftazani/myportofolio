let toastTimer;
let toastAnnouncementTimer;

function showToast(title, message, type = 'normal', duration = 3000) {
  const toastComponent = document.getElementById('toast-component');
  const toastTitle = document.getElementById('toast-title');
  const toastMessage = document.getElementById('toast-message');

  if (!toastComponent || !toastTitle || !toastMessage) return;

  // Hapus class tipe sebelumnya
  toastComponent.classList.remove('toast-success', 'toast-error', 'toast-normal');

  // Terapkan class baru berdasarkan tipe
  if (type === 'success') {
      toastComponent.classList.add('toast-success');
  } else if (type === 'error') {
      toastComponent.classList.add('toast-error');
  } else {
      toastComponent.classList.add('toast-normal');
  }

  // Perbarui konten teks
  toastTitle.textContent = title;
  toastMessage.textContent = message;

  // Dialogs make the rest of the page inert, so announce inside the active dialog.
  const announcement = document.querySelector('dialog[open] [data-toast-announcement]')
    || document.getElementById('toast-announcement');
  clearTimeout(toastAnnouncementTimer);
  if (announcement) {
      announcement.textContent = '';
      // Separate updates also announce consecutive toasts with identical text.
      toastAnnouncementTimer = setTimeout(() => {
          announcement.textContent = [title, message].filter(Boolean).join('. ');
      }, 100);
  }

  // Batalkan timer sebelumnya jika toast masih tampil
  clearTimeout(toastTimer);

  // Animasi muncul
  if (!toastComponent.matches(':popover-open')) {
      toastComponent.showPopover();
      void toastComponent.offsetHeight; // paksa browser menghitung style agar transisi berjalan
  }
  toastComponent.classList.remove('toast-hidden');
  toastComponent.classList.add('toast-show');

  // Animasi hilang otomatis
  toastTimer = setTimeout(() => {
      toastComponent.classList.remove('toast-show');
      toastComponent.classList.add('toast-hidden');
      toastTimer = setTimeout(() => toastComponent.hidePopover(), 300);
  }, duration);
}

// Django messages survive redirects. Read escaped DOM text rather than placing
// server text in executable JavaScript, and retain the banner without JS/popover.
document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('.messages-container');
  const toast = document.getElementById('toast-component');
  if (!container || !toast || typeof toast.showPopover !== 'function') return;
  const messages = [...container.querySelectorAll('.message')].map(element => ({
      text: element.textContent.trim(),
      type: element.classList.contains('error') ? 'error'
          : element.classList.contains('success') ? 'success' : 'normal',
  })).filter(message => message.text);
  if (!messages.length) return;
  container.hidden = true;
  messages.forEach((message, index) => {
      const display = () => showToast(
          message.type === 'error' ? 'Gagal' : message.type === 'success' ? 'Berhasil' : 'Informasi',
          message.text, message.type,
      );
      if (index === 0) display();
      else setTimeout(display, index * 3400);
  });
});
