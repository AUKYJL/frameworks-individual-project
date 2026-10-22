// Небольшое клиентское поведение для демонстрации подключения static JS.
const currentYear = document.getElementById("current-year");
if (currentYear) {
  currentYear.textContent = new Date().getFullYear();
}
