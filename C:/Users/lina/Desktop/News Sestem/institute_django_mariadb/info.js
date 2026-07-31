// استبدل القيم التالية بمعلوماتك الحقيقية
const person = {
  name: "اسمك هنا",
  phone: "رقمك هنا",
  address: "عنوانك هنا"
};

// عرض في الكونسول
console.log(`الاسم: ${person.name}`);
console.log(`الهاتف: ${person.phone}`);
console.log(`العنوان: ${person.address}`);

// عرض بسيط داخل الصفحة (إذا ألصقته في صفحة HTML)
if (typeof document !== "undefined") {
  document.body.innerHTML = `
    <h1>${person.name}</h1>
    <p>الهاتف: ${person.phone}</p>
    <p>العنوان: ${person.address}</p>
  `;
}
