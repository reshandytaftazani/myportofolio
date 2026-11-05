# Portofolio Pribadi dengan Django

Nama : Reshandy Taftazani Aulya

NPM : 2506547651

Kelas : PBP D

## Tentang proyek

Portofolio pribadi berbasis Django untuk menampilkan pengalaman, proyek, keterampilan, pendidikan, dan contoh kode. Antarmukanya mengusung konsep desktop multiwindow yang interaktif dan responsif pada berbagai ukuran layar. Seluruh interaksi data didukung oleh Django REST Framework (DRF) yang berjalan secara asinkron tanpa memuat ulang halaman. Proyek ini memisahkan logika validasi di serializer dan otorisasi peran di server untuk menjaga keamanan data.

### Fitur & tech stack

**Fitur Utama:**
1. *Antarmuka Desktop & Multiwindow*: Navigasi bergaya sistem operasi desktop lengkap dengan dock menu, jendela aplikasi independen, dan dukungan mode gelap/terang.
2. *Operasi Data Asinkron (CRUD)*: Penambahan, pengubahan, dan penghapusan data secara langsung menggunakan Fetch API tanpa reload halaman.
3. *Pencarian & Filter Cepat*: Pencarian berbasis teks dengan teknik debouncing dan pembatalan permintaan menggunakan `AbortController`.
4. *Interaksi Star Real-Time*: Fitur bookmark/star instan dengan pembaruan optimistis pada UI serta rollback otomatis jika terjadi kegagalan jaringan.
5. *RESTful API Terpadu*: Endpoint API lengkap untuk lima model data (`Project`, `Experience`, `Skill`, `Education`, `TechStack`) di bawah prefix `/api/v1/`.
6. *Kontrol Akses Berbasis Peran (RBAC)*: Penerapan izin server-side berbasis 4 peran (Anonim, Pengguna Terautentikasi, Editor, dan Superuser) serta validasi token CSRF.

**Tech Stack:**
- **Backend**: Python 3.13, Django (<6.0), Django REST Framework (~=3.18.3), Gunicorn
- **Frontend**: HTML5 semantik, CSS3 murni (glassmorphism, CSS grid, variables), Vanilla JavaScript (ES6+, Fetch API, AbortController, debouncing)
- **Database**: SQLite (pengembangan lokal), PostgreSQL via `psycopg2-binary` (produksi)
- **Keamanan & Utilitas**: WhiteNoise, python-dotenv, nh3 (HTML sanitizer), django-ratelimit
- **Pengujian**: Django TestCase, DRF APITestCase, Playwright (otomasi browser Chromium)

## Demo

- URL Deployment: [URL DEPLOY: ISI]
- Tangkapan Layar: [SCREENSHOT: ISI]

## Daftar isi

- [Tentang proyek](#tentang-proyek)
- [Fitur & tech stack](#fitur--tech-stack)
- [Demo](#demo)
- [Struktur folder](#struktur-folder)
- [Setup lokal](#setup-lokal)
- [Pengujian](#pengujian)
- [Referensi API & Peran](#referensi-api--peran)
- [Deployment](#deployment)
- [Progres mingguan](#progres-mingguan)
- [Refleksi Tugas 1-6](#refleksi-tutorial-dan-tugas-1)
- [AI Disclosure](#ai-disclosure)

## Struktur folder

```text
.
├── .github/          # Workflow otomatisasi GitHub Actions (deploy ke PWS)
├── main/             # Aplikasi utama Django (model, views, API DRF, serializers, tests)
├── portofolio/       # Konfigurasi proyek Django (settings, urls, wsgi, asgi)
├── static/           # Berkas aset statis (CSS, JavaScript, font, gambar)
└── templates/        # Berkas template HTML
```

## Setup lokal

Panduan instalasi dan penyiapan lingkungan lokal untuk Windows dan Linux/macOS. Dependensi aplikasi terdapat di `requirements.txt`; `requirements-dev.txt` menambahkan Playwright untuk pengujian browser.

### Windows (PowerShell)

```powershell
git clone https://github.com/reshandytaftazani/myportofolio.git
cd myportofolio
py -3.13 -m venv env
.\env\Scripts\python.exe -m pip install -r requirements-dev.txt
.\env\Scripts\python.exe -m playwright install chromium
Copy-Item .env.example .env
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py createsuperuser
.\env\Scripts\python.exe manage.py runserver
```

### Linux / macOS (Bash)

```bash
git clone https://github.com/reshandytaftazani/myportofolio.git
cd myportofolio
python3.13 -m venv env
./env/bin/python -m pip install -r requirements-dev.txt
./env/bin/python -m playwright install chromium
cp .env.example .env
./env/bin/python manage.py migrate
./env/bin/python manage.py createsuperuser
./env/bin/python manage.py runserver
```

### Konfigurasi Environment (.env)

Salin berkas `.env.example` menjadi `.env` di direktori yang sama dengan `manage.py`. Ganti placeholder `SECRET_KEY` dengan kunci acak lokal milik sendiri. Jangan commit berkas `.env`.

| Variabel | Fungsi | Contoh Nilai |
| :--- | :--- | :--- |
| `SECRET_KEY` | Kunci rahasia kriptografi untuk sesi dan keamanan Django | `django-insecure-kunci-acak-lokal-12345` |
| `DEBUG` | Mode pengembang untuk menampilkan pesan kesalahan rinci | `True` |
| `PRODUCTION` | Penentu lingkungan (`False`: SQLite lokal, `True`: PostgreSQL) | `False` |
| `ALLOWED_HOSTS` | Daftar host/domain yang diizinkan melayani permintaan | `localhost,127.0.0.1` |
| `ALLOW_PUBLIC_REGISTRATION` | Mengaktifkan atau menonaktifkan pendaftaran akun publik baru | `True` |
| `DB_NAME` | Nama database PostgreSQL (hanya saat `PRODUCTION=True`) | `pbp_db` |
| `DB_USER` | Username database PostgreSQL (hanya saat `PRODUCTION=True`) | `pbp_user` |
| `DB_PASSWORD` | Password database PostgreSQL (hanya saat `PRODUCTION=True`) | `pbp_password` |
| `DB_HOST` | Alamat host server database PostgreSQL | `localhost` |
| `DB_PORT` | Port server database PostgreSQL (default 5432) | `5432` |
| `SCHEMA` | Skema search path PostgreSQL (default `public`) | `public` |
| `EMAIL_HOST` | Host server SMTP pengiriman email (default `smtp.gmail.com`) | `smtp.gmail.com` |
| `EMAIL_PORT` | Port server SMTP pengiriman email (default 587) | `587` |
| `EMAIL_HOST_USER` | Alamat akun email pengirim | `user@example.com` |
| `EMAIL_HOST_PASSWORD` | Kata sandi atau App Password email pengirim | `rahasia123` |
| `DEFAULT_FROM_EMAIL` | Alamat email default pengirim notifikasi | `webmaster@localhost` |
| `CONTACT_RECIPIENT_EMAIL` | Alamat email penerima pesan kontak | `admin@example.com` |

Buka `http://127.0.0.1:8000/`. Tambahkan konten melalui `/dashboard/`, halaman Experience/Project, atau `/admin/` dengan akun superuser. Akun biasa dapat dibuat melalui `/register/`; untuk Editor, superuser membuat grup `Editor` jika belum ada dan menambahkan akun ke grup tersebut melalui admin. Flag `is_staff` saja tidak memberikan hak Editor atau pemilik API.

Browsable API tersedia di `/api/v1/experiences/` dan `/api/v1/projects/`; login melalui `/login/` atau `/api-auth/login/`. Gunakan `Accept: application/json` untuk JSON.

## Pengujian

Jalankan perintah berikut untuk memvalidasi konfigurasi dan menjalankan test suite:

```powershell
python manage.py check
python manage.py test main.tests_api --verbosity 2
python manage.py test main --verbosity 2
```

Hasil pengujian proyek:
- `manage.py check`: 0 issue (`0 silenced`).
- `manage.py test main.tests_api`: Pemeriksaan cepat khusus API DRF dengan 72 test lulus seluruhnya (0 failure, 0 error).
- `manage.py test main`: Suite pengujian menyeluruh yang menemukan 181 test, menjalankan 176 test, 5 di-skip, dan 0 failure/error. Suite ini membutuhkan waktu sekitar 10 menit (580 detik) karena menjalankan pengujian browser terintegrasi (Playwright) pada berbagai ukuran viewport.
- Lima test yang di-skip merupakan pengujian yang bersifat *opt-in*: 3 test peninjauan kontras visual UI (`UI_REVIEW=1`) dan 2 test audit performa Lighthouse (`UI_LIGHTHOUSE=1`).

## Referensi API & Peran

Semua endpoint berikut memakai `SessionAuthentication` dan trailing slash. Pada setiap URL dasar: `GET` membaca list dan `POST` membuat data. Detail menggunakan `{URL-dasar}{id}/` dengan `GET/PUT/PATCH/DELETE`; star menggunakan `{URL-dasar}{id}/star/` dengan `POST`. Ganti `{id}` dengan ID sebenarnya. `HEAD` tersedia pada list/detail; `OPTIONS` tetap mengikuti permission endpoint, sehingga OPTIONS star memerlukan login.

| Model | URL dasar | PK | Query list | Ordering |
| :--- | :--- | :--- | :--- | :--- |
| Project | `/api/v1/projects/` | UUID | `title`, `category` | `title`, `id` |
| Experience | `/api/v1/experiences/` | UUID | `title` atau alias `q`, `category` | `-started_at`, `title`, `id` |
| Skill | `/api/v1/skills/` | UUID | `title`, `level` | `title`, `id` |
| Education | `/api/v1/education/` | Integer | `school_name` | `-start_year`, `id` |
| TechStack | `/api/v1/techstacks/` | Integer | `name` | `order`, `id` |

Pencarian judul/nama memakai substring tanpa membedakan kapital. Category harus cocok persis; level Skill cocok penuh tanpa membedakan kapital. Nilai `all` menonaktifkan filter category/level. Filter digabungkan dengan AND. Pada Experience, title nonkosong didahulukan daripada q. List berupa array tanpa pagination; hasil kosong adalah `[]`.

### Peran

| Peran | Baca | Create | PUT/PATCH | Delete | Star |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Anonim | Ya | Tidak | Tidak | Tidak | Tidak |
| Pengguna biasa | Ya | Tidak | Tidak | Tidak | Ya |
| Editor | Ya | Tidak | Ya, kecuali Project | Tidak | Ya |
| Superuser | Ya | Ya | Ya | Ya | Ya |

Project API memakai `IsPortfolioOwnerOrReadOnly`; empat model lainnya memakai `IsPortfolioOwnerOrEditorOrReadOnly`. Star memakai `IsAuthenticated` dan aktor selalu `request.user`. Dua POST star berturut-turut menyalakan lalu mematikan star; toggle tidak idempotent. Jalur Project lama/dashboard mempunyai pemeriksaan akses tersendiri di [main/access.py](main/access.py).

### Field input

Field wajib berlaku pada POST/PUT; PATCH dapat mengirim sebagian field. Field opsional yang tidak dikirim pada update tetap mempertahankan nilai sebelumnya.

| Model | Wajib | Opsional |
| :--- | :--- | :--- |
| Project | `title`, `description` | `category`, `tech_stack`, `project_url`, `project_image_url`, `is_featured` |
| Experience | `title`, `description` | `company`, `category`, `thumbnail`, `started_at`, `ended_at` |
| Skill | `title`, `description`, `level` | `code_snippet` |
| Education | `school_name`, `period`, `detail`, `start_year` | - |
| TechStack | `name`, `icon_url`, `filename`, `code_snippet` | `order` |

Teks divalidasi dan dibersihkan sesuai method `validate_<field>` di serializer. Experience memakai category `internship`, `research`, `volunteer`, `part-time`, `full-time` (default), `freelance`, `organization`, atau `competition`. Tanggal memakai `YYYY-MM-DD` atau `null`; ended_at tidak boleh mendahului started_at. `start_year` dan `order` berupa integer; order default 0. `is_featured` berupa boolean, default false.

Skill memangkas whitespace tepi snippet dan menerima kosong/null. TechStack mewajibkan snippet non-whitespace sambil mempertahankan isi mentah, indentasi, dan newline; icon_url hanya menerima HTTP/HTTPS. Kode tetap ditampilkan sebagai teks melalui escaping/textContent. Project memetakan input tech_stack ke category bila category tidak diberikan; output tech_stack mengutamakan tags, lalu category. Tags tidak writable melalui serializer ini.

Setiap objek respons memiliki `id`, `star_count`, `is_starred`, dan `starred_by_names` (username dipisahkan koma). Semuanya read-only; input palsu diabaikan, bukan otomatis 400. Experience juga memiliki `category_display` dan `is_ongoing` read-only. Email/password tidak ditampilkan.

### Contoh Experience

Sebagai superuser dengan sesi dan token CSRF valid, kirim POST `/api/v1/experiences/` dengan JSON:

```json
{
  "title": "Software Engineer",
  "company": "Contoh Studio",
  "description": "Membangun layanan web.",
  "category": "full-time",
  "started_at": "2026-01-01",
  "ended_at": null
}
```

Respons 201 berikut memakai ID ilustrasi:

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "title": "Software Engineer",
  "company": "Contoh Studio",
  "description": "Membangun layanan web.",
  "category": "full-time",
  "category_display": "Full-Time",
  "thumbnail": null,
  "started_at": "2026-01-01",
  "ended_at": null,
  "is_ongoing": true,
  "star_count": 0,
  "is_starred": false,
  "starred_by_names": ""
}
```

PATCH ke detail dapat mengirim `{"company":"Studio Baru"}`. POST star tidak memerlukan body dan mengembalikan objek lengkap dengan star diperbarui. DELETE oleh superuser mengembalikan 204 tanpa body, sehingga tidak perlu memanggil `response.json()`.

Status utama: **200** baca/update/star berhasil; **201** create; **204** delete; **400** input tidak valid; **403** permission/CSRF; **404** data/route tidak ditemukan; **405** metode tidak didukung. Error validasi memakai nama field dan daftar pesan, sedangkan penolakan biasanya memakai `detail`.

Login pada origin yang sama dan buka `/experience/` agar token CSRF tersedia. Setiap POST/PUT/PATCH/DELETE mengirim `X-CSRFToken` dari cookie `csrftoken` atau hidden input template. Token valid tidak menggantikan permission server.

## Deployment

Branch `main` adalah branch utama pengembangan kode proyek. Otomatisasi deployment diatur oleh GitHub Actions melalui file [.github/workflows/deploy.yml](.github/workflows/deploy.yml) ("Push to PWS"). Alur kerja ini aktif saat ada push ke branch `master`, lalu secara otomatis menjalankan `git push "$PWS_URL" HEAD:refs/heads/master --force` ke server remote PWS Fasilkom UI menggunakan alamat rahasia yang disimpan di GitHub Secrets (`PWS_URL`).

Langkah deployment ke GitHub dan PWS:

```bash
git push origin main
git push origin main:master
```

URL Deployment: [URL DEPLOY: ISI]

## Progres mingguan

Ringkasan berdasarkan tanggal commit Git, bukan bukti waktu pengumpulan. Commit dapat diperiksa dengan `git show <SHA>`.

| Pekan | Jumlah commit | Progres | Contoh commit | Kendala/pelajaran |
| :--- | :---: | :--- | :--- | :--- |
| 31 Agustus - 6 September 2026 | 4 | README awal. | `55ec167`, `88b1cac`, `1148d3c`, `dc4bf70` | [ISI] |
| 7 - 13 September 2026 | 7 | Tugas 1 dan checkpoint Tutorial 2. | `5feba1c`, `0ffd21f` | [ISI] |
| 14 - 20 September 2026 | 76 | Data dinamis, form Tutorial 3, Experience, tags, dan CRUD TechStack. | `d6fb447`, `3fb5f2d`, `09ea6b9`, `7542d1f` | [ISI] |
| 21 - 27 September 2026 | 12 | Refleksi Tugas 3, Tutorial 4, dan pengembangan UI. | `108799a`, `6a25ecb`, `3a46c91` | [ISI] |
| 28 September - 4 Oktober 2026 | 24 | Registrasi/login, JavaScript Tutorial 05, dan AJAX resource. | `40407d4`, `57612c5`, `280e9f2` | [ISI] |
| 5 - 11 Oktober 2026 | 3 | Desktop multiwindow dan refleksi Tugas 5. | `3c47967`, `9a20e1d` | [ISI] |
| 12 - 18 Oktober 2026 | 0 | Tidak ada commit | - | [ISI] |
| 19 - 25 Oktober 2026 | 0 | Tidak ada commit | - | [ISI] |
| 26 Oktober - 1 November 2026 | 0 | Tidak ada commit | - | [ISI] |
| 2 - 8 November 2026 | 45 | DRF Project/Experience, test peran/CSRF, API Skill/Education/TechStack, dan perbaikan state star. | `408068b`, `77d7fa0`, `d57bf03`, `4b67418`, `8636b0c`, `984059e` | [ISI] |

Tugas 6 dikembangkan pada branch fitur dan quality, lalu digabungkan bertahap ke `main`.

## Refleksi Tutorial dan Tugas 1

**1. Penggunaan Elemen Semantik HTML5**
Ya, saya menggunakan elemen semantik HTML5 secara ekstensif pada website portofolio ini, seperti `<header>`, `<nav>`, `<main>`, `<section>`, dan `<footer>`. Penggunaan elemen-elemen ini sangat membantu dalam menyusun kerangka *static web* karena memberikan makna struktur yang jelas pada setiap bagian halaman. Sebagai contoh, memisahkan bagian profil, keahlian, teknologi, dan pendidikan ke dalam tag `<section>` masing-masing membuat kode jauh lebih mudah dibaca dan dikelola dibandingkan menggunakan tag `<div>` yang bertumpuk tanpa arti. Selain itu, elemen semantik ini juga meningkatkan aksesibilitas web dan optimisasi mesin pencari (SEO).

**2. Tantangan Tata Letak Responsif (CSS)**
Tantangan utama dalam membuat tata letak yang responsif adalah mengadaptasi desain multi-kolom agar tetap terbaca dan tidak terkesan sempit saat dibuka di layar *mobile*. Pada layar *desktop*, saya merancang bagian *Profile/Hero* dengan tata letak dua kolom dan bagian *Skills* dengan tiga kolom sejajar. 

Untuk mengevaluasinya saat berpindah ke *mobile*, saya memprioritaskan alur membaca natural (dari atas ke bawah) dan keterbacaan teks. Menggunakan CSS Grid dan `@media queries`, saya mengubah urutan grid dan memaksanya menjadi satu kolom (`grid-template-columns: 1fr`). Prioritas utama adalah memastikan ukuran teks tetap proporsional dan tidak ada elemen (seperti foto avatar atau kartu *skill*) yang terpotong karena batasan lebar layar.

**3. Batasan Static Web dan Rencana Fungsionalitas Dinamis**
Batasan utama yang saya rasakan dari *static web* murni adalah ketidakmampuan untuk melakukan pembaruan konten secara efisien (tidak *scalable*). Saat ini, jika saya ingin menambahkan proyek baru, mengubah nilai IPK, atau memperbarui daftar *skills*, saya harus membuka file HTML, mengubah kodenya secara manual (secara *hardcode*), dan melakukan *deployment* ulang. 

Berdasarkan batasan tersebut, fungsionalitas dinamis utama yang ingin saya tambahkan pada iterasi proyek selanjutnya menggunakan arsitektur MVT Django adalah integrasi *database* dan panel admin. Saya ingin membuat halaman portofolio yang datanya ditarik langsung dari *database* (melalui *Models*), sehingga saya dapat menambah, mengedit, atau menghapus konten portofolio melalui antarmuka admin tanpa perlu menyentuh kode HTML lagi.

### Tugas 2

1. **Alur ketika pengguna membuka halaman portofolio baru:**
   - **Permintaan (Request):** Pengguna memasukkan URL di browser, yang mengirimkan HTTP Request ke server Django proyek.
   - **urls.py Proyek:** Django pertama kali mengecek konfigurasi URL utama (`portofolio/urls.py`). Jika URL cocok, Django akan meneruskan request tersebut ke `urls.py` tingkat aplikasi.
   - **urls.py Aplikasi:** Di dalam aplikasi (`main/urls.py`), Django mencocokkan URL dengan *path* yang ada untuk menentukan fungsi **View** mana yang harus dipanggil.
   - **View:** Fungsi view (di `main/views.py`) menerima request tersebut dan memproses logika bisnisnya.
   - **Model:** Jika view membutuhkan data (misalnya daftar portofolio), view akan meminta data tersebut melalui **Model** (`main/models.py`), yang kemudian mengambilnya dari *database*.
   - **Template:** Setelah view mendapatkan data, view menyisipkan data tersebut ke dalam sebuah **Template** (file HTML). Template merender tampilan antarmuka yang dinamis menggunakan *template tags*.
   - **Respons (Response):** View mengembalikan template yang sudah dirender menjadi sebuah HTTP Response ke browser pengguna untuk ditampilkan.

2. **Mengapa data disimpan pada Model dan tidak ditulis langsung di Template:**
   - Menyimpan data di **Model** memisahkan antara logika data dan tampilan (*Separation of Concerns*). Jika kita melakukan *hardcode* di template, setiap kali ada proyek baru atau perubahan teks, kita harus mengedit file HTML secara manual.
   - **Dampaknya terhadap pemeliharaan:** Membuat aplikasi jauh lebih mudah dikelola (*maintainable*) dan *scalable*. Data bisa diubah secara dinamis lewat *database* (misal via Django Admin) tanpa menyentuh kode. Hal ini juga meminimalisir risiko *error* pada kode HTML saat melakukan perubahan konten.

3. **Perbedaan fungsi makemigrations dan migrate:**
   - **makemigrations:** Perintah ini digunakan untuk memindai perubahan yang kita buat pada file `models.py` (seperti membuat model baru, menambah/menghapus *field*) dan menghasilkan sebuah file migrasi baru. File ini hanya berupa instruksi/catatan perubahan skema, namun belum diterapkan ke *database*.
   - **migrate:** Perintah ini digunakan untuk mengeksekusi instruksi dari file migrasi tersebut agar diterapkan langsung ke dalam *database* sungguhan. Perintah ini yang benar-benar mengubah atau membuat tabel di dalam *database*.
   - **Contoh perubahan:** Misalkan kita memiliki model `Portofolio` dengan field `judul` dan `deskripsi`. Suatu saat, kita ingin menambahkan *field* baru berupa `link_proyek`. Kita menambahkannya di `models.py`. Kita **harus** menjalankan `python manage.py makemigrations` agar Django membuat file instruksi penambahan kolom tersebut. Setelah itu, kita **harus** menjalankan `python manage.py migrate` agar kolom `link_proyek` benar-benar ditambahkan ke dalam tabel di database SQLite/PostgreSQL kita.

### Tugas 3

1. **Mengapa menggunakan ModelForm dan {% csrf_token %}:**
   - **ModelForm:** Kita menggunakan ModelForm pada Django alih-alih form HTML manual karena ModelForm secara otomatis menghasilkan form (termasuk validasi dan tipe input HTML) berdasarkan atribut field yang telah kita definisikan di dalam Model. Hal ini mencegah pengulangan penulisan kode (*Don't Repeat Yourself*), membuat penanganan dan validasi data lebih praktis, serta mempermudah penyimpanan data (pembuatan objek) ke *database* dengan aman hanya dengan memanggil metode `.save()`.
   - **{% csrf_token %}:** Kita diwajibkan menambahkan token ini sebagai bentuk keamanan untuk melindungi dari serangan CSRF (*Cross-Site Request Forgery*). Token yang di-*generate* secara unik oleh server pada form ini berfungsi untuk memastikan bahwa saat ada *request* POST masuk ke server, form tersebut benar-benar di-*submit* dari dalam halaman web kita, dan bukan dipalsukan oleh aplikasi pihak ketiga atau *script* peretas yang mencoba mengeksekusi sesuatu tanpa izin user.

2. **Mengapa JSON lebih disukai dibandingkan XML:**
   - JSON (*JavaScript Object Notation*) lebih ringan dan format strukturnya (*key-value pair*) jauh lebih ringkas dibandingkan XML yang mengharuskan penulisan tag pembuka dan penutup (seperti HTML).
   - JSON secara *native* lebih mudah dibaca, di-*parse*, dan digunakan terutama oleh JavaScript, yang merupakan bahasa pemrograman paling banyak dipakai pada pengembangan *frontend* (React, Vue) dan *backend* modern (Node.js).
   - Karena file JSON lebih kecil dari XML (berkat efisiensi strukturnya), JSON membutuhkan bandwidth yang lebih sedikit dan mempercepat perpindahan transfer data via internet (proses respon API).

3. **Alur fungsi view mengembalikan data JSON dan pentingnya proses serialization:**
   - **Alur yang terjadi:** Ketika pengguna atau klien mengakses URL tertentu, Django akan meneruskan *request* ke fungsi *view*. *View* akan mengambil objek data (mengirim *query* ke database) dari Model (misalnya `Portofolio.objects.all()`). Data hasil *query* tersebut kemudian akan dimasukkan ke fungsi serializer untuk dikonversikan ke dalam format data bawaan seperti XML atau JSON. Kemudian, view akan mereturn hasil output serialisasi tadi dibungkus oleh `HttpResponse` (dengan mendeklarasikan `content_type="application/json"`) agar diubah menjadi respon HTTP yang bisa dibaca klien.
   - **Mengapa perlu serialization:** Data hasil pengambilan dari *database* via Django Model (*QuerySet*) adalah tipe objek kompleks milik bahasa Python. Klien (seperti *browser* atau aplikasi eksternal) tidak akan mengerti objek kompleks Python tersebut. Proses *serialization* berfungsi sebagai penterjemah atau jembatan untuk mengonversi data berupa objek Python kompleks tersebut ke dalam tipe data *native* Python sederhana (seperti *dictionary*, *list*, integer, *string*) yang mana selanjutnya dapat dengan mudah direpresentasikan (di-render) menjadi string format JSON biasa.

### Tugas 5

1. **Apa itu debouncing dan mengapa penting pada pencarian AJAX:**

   Debouncing adalah teknik menunda eksekusi fungsi sampai tidak ada pemanggilan baru selama jeda tertentu. Pada fitur pencarian, misalnya dengan jeda 300 milidetik, setiap perubahan input membatalkan timer sebelumnya dan membuat timer baru. Request AJAX baru dikirim ketika pengguna berhenti mengetik selama jeda tersebut. Dengan demikian, saat pengguna mengetik kata `django` dengan cepat, aplikasi cukup mengirim pencarian untuk kata terakhir, bukan satu request untuk setiap huruf.

   Teknik ini mengurangi jumlah request, penggunaan bandwidth, dan beban server, serta menghindari pembaruan hasil yang terlalu sering sehingga pencarian terasa lebih nyaman. Namun, debouncing tidak menjamin urutan respons request yang sudah terkirim. Agar hasil pencarian lama tidak menimpa hasil terbaru, aplikasi dapat membatalkan request sebelumnya menggunakan `AbortController` atau memeriksa apakah respons masih sesuai dengan input terbaru. Referensi: [MDN tentang debounce](https://developer.mozilla.org/en-US/docs/Glossary/Debounce).

2. **Fungsi await ketika menggunakan fetch() dan akibat jika tidak digunakan:**

   `fetch()` mengembalikan sebuah `Promise`. Dalam fungsi `async`, `await fetch(url)` menunda kelanjutan fungsi tersebut sampai Promise selesai, lalu menghasilkan objek `Response` jika berhasil. Proses ini tidak memblokir seluruh browser, sehingga antarmuka tetap dapat merespons interaksi pengguna. Untuk membaca body sebagai JSON, kita juga menggunakan `await response.json()` karena metode tersebut mengembalikan Promise. Contohnya:

   ```javascript
   async function ambilData(url) {
     const response = await fetch(url);
     if (!response.ok) {
       throw new Error(`HTTP ${response.status}`);
     }
     const data = await response.json();
     return data;
   }
   ```

   Jika ditulis `const response = fetch(url)` tanpa `await`, request tetap berjalan, tetapi variabel `response` berisi Promise, bukan objek Response. Kode berikutnya langsung berlanjut, sehingga memanggil `response.json()` akan menghasilkan error karena metode tersebut tidak tersedia pada Promise. Tanpa `await`, kita tetap bisa menangani hasil dengan `.then()` dan kegagalan dengan `.catch()`. Selain itu, `fetch()` tidak otomatis menolak Promise untuk status HTTP seperti 404 atau 500, sehingga `response.ok` perlu diperiksa seperti pada contoh. Referensi: [MDN tentang penggunaan Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch).

3. **Apa itu XSS dan mengapa penampilan data melalui AJAX/JavaScript dapat lebih rentan:**

   XSS (*Cross-Site Scripting*) adalah serangan ketika penyerang menyisipkan kode berbahaya ke halaman web sehingga kode tersebut dijalankan oleh browser pengguna dalam konteks situs itu. Akibatnya, penyerang dapat membaca data yang dapat diakses JavaScript, mengubah tampilan, atau melakukan tindakan menggunakan sesi pengguna.

   Template Django secara default melakukan *autoescaping* pada variabel seperti `{{ nama }}`. Karakter khusus HTML, misalnya `<` dan `>`, diubah menjadi representasi aman sehingga input ditampilkan sebagai teks. Sebaliknya, data JSON yang diterima melalui AJAX tidak otomatis mendapatkan perlindungan template tersebut ketika JavaScript memasukkannya ke DOM. Jika data yang tidak tepercaya dimasukkan melalui `innerHTML`, browser akan menafsirkannya sebagai HTML, dan atribut event berbahaya dapat menjalankan JavaScript. Referensi: [dokumentasi keamanan Django](https://docs.djangoproject.com/en/6.0/topics/security/#cross-site-scripting-xss-protection) dan [MDN tentang risiko innerHTML](https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML#security_considerations).

   Jadi, tingkat kerentanannya bergantung pada cara data ditampilkan. Untuk teks biasa, gunakan `textContent`, misalnya `elemen.textContent = data.nama`, agar data diperlakukan sebagai teks. Jika memang perlu menampilkan HTML dari sumber yang tidak tepercaya, gunakan sanitizer HTML yang terawat sebelum memasukkannya ke DOM. Template Django juga tetap dapat rentan jika perlindungannya dilewati menggunakan filter `safe`, `mark_safe`, atau menonaktifkan autoescaping; escaping HTML juga tidak otomatis melindungi semua konteks seperti JavaScript atau URL.

### Tugas 6

1. **REST, JSON, PUT, dan PATCH**

   REST adalah gaya arsitektur dengan batasan client-server, stateless, cache, uniform interface, dan layered system; code-on-demand opsional. Resource dikenali melalui URI dan dimanipulasi melalui representasi dengan semantik yang jelas. JSON hanya format data; mengembalikan JSON sambil menghapus data lewat GET, misalnya, belum memenuhi rancangan REST. Uniform interface juga mencakup hypermedia. API proyek ini memakai sesi server dan belum menyediakan navigasi hypermedia, sehingga penggunaan DRF sendiri tidak membuktikan seluruh batasan REST murni. Referensi: [Fielding tentang REST](https://ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm).

   PUT menyatakan penggantian representasi resource, misalnya menyimpan seluruh formulir Experience. PATCH mengubah sebagian, misalnya `{"company":"Studio Baru"}`. PUT memiliki semantik idempotent; PATCH tidak dijamin idempotent secara umum. Pada kode ini, `partial=True` hanya dipakai untuk PATCH. PUT memerlukan seluruh field wajib, tetapi field opsional yang tidak dikirim tetap mempertahankan nilai sebelumnya. Untuk menghapus tanggal akhir, kirim `"ended_at":null` secara eksplisit. Referensi: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-put) dan [RFC 5789](https://www.rfc-editor.org/rfc/rfc5789.html).

2. **Serializer dibandingkan dictionary manual dan JsonResponse**

   Serializer mengubah model menjadi data sederhana dan memvalidasi input sebelum disimpan. ModelSerializer menyediakan pemetaan field, pemeriksaan tipe, error per field, serta create/update yang dapat disesuaikan. Dictionary manual dan JsonResponse membutuhkan logika validasi/representasi yang dirakit sendiri; JsonResponse hanya membentuk respons JSON. Referensi: [serializer DRF](https://www.django-rest-framework.org/api-guide/serializers/).

   ExperienceSerializer memakai fields eksplisit, membersihkan teks melalui `validate_<field>`, dan memeriksa hubungan tanggal dalam `validate`. Informasi star serta category_display/is_ongoing bersifat read-only; email/password tidak diserialisasikan. Field hasil perhitungan yang dikirim klien diabaikan. Permission tetap diperiksa pada permission class, dan output tetap di-escape saat dimasukkan ke DOM.

3. **Autentikasi dan otorisasi**

   Autentikasi menentukan identitas pengguna; SessionAuthentication mengenali akun dari sesi Django. Otorisasi menentukan tindakan yang boleh dilakukan akun tersebut. Login tidak otomatis memberikan hak create/update/delete. Untuk Experience, permission class mengizinkan Editor melakukan PUT/PATCH dan membatasi create/delete kepada superuser. Pengguna biasa dapat membaca dan memberi star; Project API membatasi mutasi CRUD kepada superuser. Referensi: [autentikasi DRF](https://www.django-rest-framework.org/api-guide/authentication/).

   Tombol tersembunyi hanya mengatur tampilan. Pengguna masih dapat mengirim request langsung melalui fetch atau klien lain, sehingga permission harus diperiksa di server. Test penolakan juga memeriksa record/relasi yang relevan tetap tidak berubah, bukan hanya status 403. Aktor star diambil dari request.user, bukan ID akun pada body.

4. **CSRF pada SessionAuthentication dan force_authenticate**

   Browser otomatis mengirim cookie sesi. Request dari situs lain dapat mencoba menyalahgunakan sesi tersebut, sehingga mutasi POST/PUT/PATCH/DELETE yang terautentikasi melalui SessionAuthentication memerlukan token CSRF valid. Experience menyediakan token melalui template/cookie dan mengirim header X-CSRFToken. Token tersebut tidak memberikan hak di luar peran akun dan tidak menggantikan escaping untuk mencegah XSS. Referensi: [SessionAuthentication dan CSRF](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication).

   force_authenticate memasang identitas uji langsung dan melewati autentikasi DRF normal. Cara ini membantu menguji permission, tetapi tidak membuktikan login atau CSRF sesi. Karena itu, test CSRF memakai APIClient(enforce_csrf_checks=True), memastikan `.login()` berhasil, mengirim mutasi tanpa token untuk memperoleh 403 dan memeriksa data tetap, lalu memeriksa request dengan token valid. Referensi: [pengujian CSRF DRF](https://www.django-rest-framework.org/api-guide/testing/#csrf-validation).

### AI Disclosure

Dalam pengerjaan tugas dan eksplorasi proyek ini, saya menggunakan bantuan AI untuk menganalisis masalah teknis, memahami proses deployment, memperbaiki UI, dan memperbaiki kekurangan dalam penulisan sintaks kode. Rincian penggunaan AI dicatat dalam satu bagian berikut.

**Alat yang Digunakan:** Antigravity (powered by Google Gemini), Claude.ai, gemini.google, dan OpenAI Codex.

**Strategi Prompting:**

1. Memberikan pesan *error* dari terminal atau browser, seperti error CSRF dan penolakan `git push`, beserta konteks masalah agar AI dapat membantu menganalisis penyebab dan langkah penyelesaiannya. Untuk masalah tampilan, saya menjelaskan perilaku header saat mode gelap diaktifkan.
2. Mengajukan pertanyaan deskriptif, misalnya apakah data akan terhapus setelah commit dan redeploy, untuk memahami alur kerja sistem *production* PWS dan penyimpanan data pada lingkungan deployment.
3. Menjelaskan kekurangan pada UI dan memberikan potongan kode yang bermasalah agar AI dapat memberikan saran perbaikan tampilan serta membantu mengidentifikasi kesalahan sintaks.

**Bagian Spesifik yang Dibantu oleh AI:**

1. **Debugging Django:** AI membantu menganalisis error 403 CSRF dan memberikan arahan untuk menambahkan URL PWS ke dalam `CSRF_TRUSTED_ORIGINS` di `settings.py`.
2. **Manajemen Git:** AI membantu menjelaskan penyelesaian konflik saat `git push`, penggunaan `git pull --rebase` untuk menyinkronkan repository lokal dengan GitHub, serta penggunaan *force push* ke PWS.
3. **Pemahaman Infrastruktur Deployment:** AI membantu menjelaskan hubungan antara lingkungan deployment, penyimpanan sementara, dan kemungkinan perubahan atau hilangnya data `db.sqlite3` setelah redeployment.
4. **Analisis Bug Tampilan:** AI membantu menganalisis penyebab header tidak berubah warna saat mode gelap diaktifkan.
5. **Perbaikan UI:** AI membantu mengevaluasi kekurangan UI dan memberikan saran perbaikan agar tampilan website lebih rapi, konsisten, dan mudah digunakan.
6. **Perbaikan Sintaks Kode:** AI membantu mengidentifikasi dan memperbaiki kesalahan atau kekurangan dalam penulisan sintaks kode, serta menjelaskan perbaikan yang diperlukan.
