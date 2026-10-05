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
