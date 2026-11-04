# Tahap 1 — baseline

Branch: `fix/tugas-6-baseline`. Verifikasi kode akhir: `4feeeb5`.
Laporan ini ditambahkan setelah seluruh verifikasi kode selesai. Tidak ada merge,
push, pekerjaan Tahap 2, atau perubahan AI disclosure dalam sesi ini.

## Kondisi awal yang diverifikasi

- Working tree bersih pada branch yang diminta, HEAD `be7e9b2`.
- Dua belas commit terakhir diperiksa melalui `git log -12 --oneline`.
- Hasil suite dari handoff diperlakukan sebagai laporan, bukan hasil run sesi ini.

## Diagnosis dan perubahan

### Experience

Test pencarian awal gagal pada visibility loading. Test mengamati URL lama
`/api/experience/?q=`, sementara browser mengirim
`/api/v1/experiences/?title=...`. Kata `Acme` adalah perusahaan fixture;
API memfilter substring judul/peran. Respons cepat juga dapat menyelesaikan
loading sebelum assertion membacanya.

Test sekarang mengirim burst input `D`, `Dev`, `Developer` dalam satu browser
turn dan menahan request koleksi v1 yang sesuai. Test memeriksa query `title`,
satu request tertahan, loading dan `aria-busy` saat request berjalan, lalu
melepas respons API nyata dan memeriksa hasil serta berakhirnya loading.
State kosong tetap diperiksa setelah pencarian `missing`.

Kontrak UI yang dipertahankan: selama debounce 300 ms, hasil sebelumnya tetap
tersedia; loading jaringan dimulai ketika fetch dimulai. Selama request,
hasil sebelumnya tetap tersedia dengan `aria-busy=true` dan status loading
untuk pembaca layar. Sukses mengganti hasil; respons kosong menampilkan empty
state; kegagalan menampilkan error/retry dan mempertahankan konten yang ada.
AbortController, pemeriksaan request terbaru, kategori, star, dan peran tidak
diubah.

Bagian XSS berikutnya mengungkap selector error lama
`#id_experience_title_error` dan ekspektasi pesan `sanitasi` yang tidak sesuai
API. Test menggunakan field error aktual, memeriksa `aria-invalid`, dan pesan
`Title cannot be empty.`. Pengujian penolakan payload kosong setelah sanitasi,
penyimpanan judul aman, tidak adanya `onerror`, dan tidak adanya alert tetap ada.

Review `min-height: 1px` menemukan bahwa kontainer kosong dianggap visible tanpa
membuktikan konten fallback. Setelah assertion diarahkan ke kartu, test gagal:
Experience tidak memuat data ketika desktop gagal boot, karena menunggu event
`desktop:open`. Listener `load` kini mengaktifkan fetch jika desktop tidak siap,
selaras dengan resource publik lainnya. Tinggi semu dihapus; test memeriksa dua
kartu dan judul yang terlihat, baik saat script desktop gagal dimuat maupun
saat inisialisasinya melempar error.

### Intercept Project dan Experience

Pola yang sebelumnya diperluas dibatasi ke path koleksi v1 yang tepat, dengan
query opsional. Pola tidak menangkap endpoint detail/star atau resource lain.
Wrapper fetch retry Project juga membandingkan pathname secara tepat.
Isolasi request Project dalam test fallback diperbarui ke koleksi v1.

### Dock

Test asli diulang enam kali: tiga lulus, tiga gagal. Ketiga failure membaca
`x=823.4241943359375` alih-alih resting `x=809.5` segera setelah
`emulate_media(reduced_motion='reduce')`: selisih 13.9241943359375 px, yaitu
posisi hover yang belum dibersihkan listener media asynchronous.

Review `dock.js` menunjukkan `refresh()` memanggil `reset()`, membatalkan
requestAnimationFrame, menghapus properti transform ikon/divider, memperbarui
atribut motion, dan mengukur ulang layout. Test kini menunggu atribut
`data-dock-motion` dilepas dan animasi selesai sebelum membaca geometri.
Assertion posisi asli (`places=1`) dipertahankan; tidak ada koordinat baru,
pelebaran toleransi, atau sleep tambahan.

Test tambahan memeriksa reduced motion sejak sebelum navigasi, pengaktifan
kembali animasi, lalu reduced motion saat skala ikon berada di antara posisi
awal dan target. Test memeriksa semua properti transform dibersihkan dan
divider kembali ke posisi resting. Tidak ada perubahan aplikasi Dock.

## Bukti verifikasi sesi ini

Semua perintah Django menggunakan `.\env\Scripts\python.exe`.

| Pemeriksaan | Test | Failure | Error | Skip | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reproduksi awal Experience + separator Dock | 2 | 1 | 0 | 0 | 1 |
| Enam test terkait Experience, fallback, retry dan intercept | 6 | 0 | 0 | 0 | 0 |
| Fallback setelah penyempurnaan isolasi request | 1 | 0 | 0 | 0 | 0 |
| Dock asli: enam run terpisah, satu test/run | 6 total | 3 | 0 | 0 | 3 run exit 1, 3 exit 0 |
| Dock setelah perbaikan: enam run terpisah, dua test/run | 12 total | 0 | 0 | 0 | Semua 0 |
| `manage.py check` | — | — | — | — | 0; 0 issues |
| `manage.py test main.tests_api --verbosity 1` | 29 | 0 | 0 | 0 | 0 |
| `manage.py test main --verbosity 2` | 133 | 0 | 0 | 5 | 0 |

Suite API: 137.905 detik. Full suite tunggal: 594.807 detik.
Jumlah 133 mencakup lima skip; 128 test benar-benar dieksekusi.
Diff kerja dan staged diff diperiksa sebelum commit perbaikan.

### Skip dan batas pemeriksaan

- `IncompleteContrastReviewTests.test_css_states_roles_and_emulated_touch_rotation`:
  opt-in `UI_REVIEW=1` tidak diaktifkan; audit state CSS/kontras tersebut belum diuji.
- `IncompleteContrastReviewTests.test_historical_flags_with_revealed_elements`:
  opt-in `UI_REVIEW=1` tidak diaktifkan; review temuan aksesibilitas historis belum diuji.
- `LighthouseEvidenceTests.test_mobile_public_routes`:
  opt-in `UI_LIGHTHOUSE=1` tidak diaktifkan; metrik Lighthouse home/Project belum diuji.
- `LighthouseEvidenceTests.test_mobile_remaining_public_routes`:
  opt-in `UI_LIGHTHOUSE=1` tidak diaktifkan; metrik Lighthouse rute lainnya belum diuji.
- `AdditionalUIStateTests.test_loaded_libraries_and_interaction_contrast`:
  opt-in `UI_REVIEW=1` tidak diaktifkan; audit library/kontras interaksi tersebut belum diuji.

Browser menggunakan konfigurasi default test: Edge headless. Tidak dilakukan run
terpisah Firefox/Chrome atau audit axe opt-in. Pemeriksaan layout responsif rutin
tetap berjalan, termasuk matriks 7 lebar × 2 tema × 15 rute. Peringatan direktori
`staticfiles/` yang belum tersedia muncul pada test server; verifikasi ini tidak
membuktikan kesiapan collectstatic atau deployment production.

## Catatan bukti bantuan AI — bukan disclosure final

- Instruksi pengguna: selesaikan baseline, reproduksi masalah terlebih dahulu,
  pertahankan cakupan, gunakan respons tertahan untuk loading, ulangi Dock,
  commit lokal, dan jangan merge/push/memulai Tahap 2.
- OpenAI Codex membaca kode/test, menjalankan reproduksi, membuat perubahan
  aplikasi/test di atas, meninjau diff, membuat commit lokal, dan menjalankan
  verifikasi. Perubahan ini dibuat agent, bukan diklaim sebagai koreksi manual
  mahasiswa.
- Koreksi atas handoff: tinggi kontainer 1px tidak membuktikan fallback bekerja;
  test konten bermakna mengungkap fetch yang belum dimulai. Agent memperbaiki
  inisialisasi fallback dan menghapus tinggi semu.
- Keterbatasan nyata selama sesi: satu pemanggilan test memakai nama kelas
  `UIAuditBrowserTests` yang tidak ada, menghasilkan loader error. Agent membaca
  kelas aktual `UIPlanBrowserTests`, memperbaiki perintah, dan menjalankannya
  kembali dengan sukses. Run antara juga mengungkap selector/pesan modal lama
  serta fallback belum memuat kartu; hasil gagal tersebut tidak dianggap lulus.
- Hasil final dan batas cakupan dicatat di atas. README dan AI disclosure lama
  dipertahankan; finalisasi disclosure tetap pekerjaan tahap terakhir terpisah.
