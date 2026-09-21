Nama : Reshandy Taftazani Aulya

NPM : 2506547651

Kelas : PBP D

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

### AI Disclosure

Dalam pengerjaan tugas dan eksplorasi proyek ini, saya menggunakan **Antigravity (Gemini AI Coding Assistant)** yang terintegrasi di dalam *code editor* dengan rincian sebagai berikut:

- **Alat yang Digunakan:** Antigravity (powered by Google Gemini), Claude.ai, gemini.google.
- **Strategi Prompting:** 
  1. Memberikan *copy-paste* pesan *error* langsung dari terminal atau browser (contoh: *error* CSRF dan *error* Git *reject*) agar AI dapat menganalisis penyebab teknis secara spesifik.
  2. Memberikan instruksi pertanyaan deskriptif (misal: "apakah nanti setelah saya commit lagi dan redeploy akan reset lagi datanya") untuk memahami alur kerja di sistem *production* PWS.
  3. Meminta AI untuk menyusun kerangka jawaban reflektif berdasarkan materi yang telah dipelajari di tutorial.
- **Bagian Spesifik yang Dibantu oleh AI:**
  1. **Debugging Django:** Menemukan dan memperbaiki error 403 CSRF dengan menambahkan URL PWS ke dalam `CSRF_TRUSTED_ORIGINS` di `settings.py`.
  2. **Manajemen Git:** Menyelesaikan konflik saat `git push` dengan menggunakan `git pull --rebase` untuk menyinkronkan *repository* lokal dengan GitHub, serta melakukan *force push* ke PWS.
  3. **Pemahaman Infrastruktur Deployment:** Menjelaskan cara kerja server yang bersifat *ephemeral* (sementara) pada PWS yang menyebabkan data `db.sqlite3` mereset setelah *redeployment*.
  4. **Bug Dalam Implementasi Kode:** Terdapat bug dimana header tidak berubah warna ketika menjalankan mode dark sehingga meminta bantuan AI untuk menganalisis letak error dari kode tersebut.

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

### AI Disclosure

Dalam pengerjaan tugas dan eksplorasi proyek ini, saya menggunakan **Antigravity (Gemini AI Coding Assistant)** yang terintegrasi di dalam *code editor* dengan rincian sebagai berikut:

- **Alat yang Digunakan:** Antigravity (powered by Google Gemini), Claude.ai, gemini.google.
- **Strategi Prompting:** 
  1. Memberikan *copy-paste* pesan *error* langsung dari terminal atau browser (contoh: *error* CSRF dan *error* Git *reject*) agar AI dapat menganalisis penyebab teknis secara spesifik.
  2. Memberikan instruksi pertanyaan deskriptif (misal: "apakah nanti setelah saya commit lagi dan redeploy akan reset lagi datanya") untuk memahami alur kerja di sistem *production* PWS.
- **Bagian Spesifik yang Dibantu oleh AI:**
  1. **Debugging Django:** Menemukan dan memperbaiki error 403 CSRF dengan menambahkan URL PWS ke dalam `CSRF_TRUSTED_ORIGINS` di `settings.py`.
  2. **Manajemen Git:** Menyelesaikan konflik saat `git push` dengan menggunakan `git pull --rebase` untuk menyinkronkan *repository* lokal dengan GitHub, serta melakukan *force push* ke PWS.
  3. **Pemahaman Infrastruktur Deployment:** Menjelaskan cara kerja server yang bersifat *ephemeral* (sementara) pada PWS yang menyebabkan data `db.sqlite3` mereset setelah *redeployment*.
  4. **Bug Dalam Implementasi Kode:** Terdapat bug dimana header tidak berubah warna ketika menjalankan mode dark sehingga meminta bantuan AI untuk menganalisis letak error dari kode tersebut.