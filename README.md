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