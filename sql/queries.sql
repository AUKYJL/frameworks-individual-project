-- ПР7. Именованные запросы SQLite. Каждый запрос выполняется и проверяется
-- в тестах, а результаты используются Django-страницами. ? = параметры.
-- ГРУППА 1. Простые списки SELECT (минимум два).

-- name: list_users
SELECT id, name, email FROM users ORDER BY name, id;

-- name: list_categories
SELECT id, name, description FROM categories ORDER BY name, id;

-- name: list_times
SELECT id, label, moment FROM times ORDER BY moment, id;

-- name: list_tasks
SELECT id, title, description, user_id, category_id, is_completed
FROM tasks ORDER BY id;

-- ГРУППА 2. WHERE: отбор записей по условиям (минимум два).

-- name: tasks_by_status
SELECT id, title, is_completed FROM tasks
WHERE is_completed = ? ORDER BY id;

-- name: reminders_before
SELECT id, text, remind_at FROM reminders
WHERE remind_at <= ? ORDER BY remind_at, id;

-- name: tasks_for_user
SELECT id, title, is_completed FROM tasks
WHERE user_id = ? ORDER BY id;

-- name: reminders_for_user
SELECT r.id, r.text, r.remind_at, c.name AS category
FROM reminders AS r JOIN categories AS c ON c.id = r.category_id
WHERE r.user_id = ? ORDER BY r.remind_at, r.id;

-- name: tasks_for_category
SELECT id, title, is_completed FROM tasks
WHERE category_id = ? ORDER BY id;

-- name: reminders_for_category
SELECT r.id, r.text, r.remind_at, c.name AS category
FROM reminders AS r JOIN categories AS c ON c.id = r.category_id
WHERE r.category_id = ? ORDER BY r.remind_at, r.id;

-- name: reminders_for_time
SELECT r.id, r.text, r.remind_at, c.name AS category
FROM reminders AS r JOIN categories AS c ON c.id = r.category_id
WHERE r.time_id = ? ORDER BY r.id;

-- ГРУППА 3. JOIN: получить данные связанных сущностей (минимум два).

-- name: joined_tasks
SELECT t.*, u.name AS user_name, c.name AS category_name
FROM tasks AS t
JOIN users AS u ON u.id = t.user_id
JOIN categories AS c ON c.id = t.category_id
ORDER BY t.id;

-- name: joined_reminders
SELECT r.*, c.name AS category, u.name AS user_name,
       t.title AS task_title, tm.label AS time_label
FROM reminders AS r
JOIN categories AS c ON c.id = r.category_id
LEFT JOIN users AS u ON u.id = r.user_id
LEFT JOIN tasks AS t ON t.id = r.task_id
LEFT JOIN times AS tm ON tm.id = r.time_id
ORDER BY r.remind_at, r.id;

-- name: task_detail
SELECT t.*, u.name AS user_name, c.name AS category_name
FROM tasks AS t
JOIN users AS u ON u.id = t.user_id
JOIN categories AS c ON c.id = t.category_id
WHERE t.id = ?;

-- name: reminder_detail
SELECT r.*, c.name AS category, u.name AS user_name,
       t.title AS task_title, tm.label AS time_label
FROM reminders AS r
JOIN categories AS c ON c.id = r.category_id
LEFT JOIN users AS u ON u.id = r.user_id
LEFT JOIN tasks AS t ON t.id = r.task_id
LEFT JOIN times AS tm ON tm.id = r.time_id
WHERE r.id = ?;

-- name: search_reminders
-- Прежний запрос ПР7 с четырьмя параметрами, оставлен для совместимости.
SELECT r.*, c.name AS category, u.name AS user_name
FROM reminders AS r
JOIN categories AS c ON c.id = r.category_id
LEFT JOIN users AS u ON u.id = r.user_id
WHERE (? = '' OR r.text LIKE '%' || ? || '%')
  AND (? = 0 OR r.category_id = ?)
ORDER BY r.remind_at, r.id;

-- name: search_reminders_filtered
SELECT r.*, c.name AS category, u.name AS user_name,
       t.title AS task_title, tm.label AS time_label
FROM reminders AS r
JOIN categories AS c ON c.id = r.category_id
LEFT JOIN users AS u ON u.id = r.user_id
LEFT JOIN tasks AS t ON t.id = r.task_id
LEFT JOIN times AS tm ON tm.id = r.time_id
WHERE (? = '' OR r.text LIKE '%' || ? || '%')
  AND (? = 0 OR r.category_id = ?)
  AND (? = '' OR r.remind_at <= ?)
  AND (? = 'all' OR CASE
       WHEN r.remind_at > ? THEN 'upcoming'
       WHEN r.remind_at = ? THEN 'current'
       ELSE 'overdue' END = ?)
ORDER BY r.remind_at, r.id;

-- name: search_tasks
SELECT t.*, u.name AS user_name, c.name AS category_name
FROM tasks AS t
JOIN users AS u ON u.id = t.user_id
JOIN categories AS c ON c.id = t.category_id
WHERE (? = '' OR t.title LIKE '%' || ? || '%'
                 OR t.description LIKE '%' || ? || '%')
  AND (? = 'all' OR t.is_completed = ?)
  AND (? = 0 OR t.category_id = ?)
ORDER BY t.id;

-- name: search_users
SELECT id, name, email FROM users
WHERE (? = '' OR name LIKE '%' || ? || '%'
              OR email LIKE '%' || ? || '%')
ORDER BY name, id;

-- name: search_categories
SELECT id, name, description FROM categories
WHERE (? = '' OR name LIKE '%' || ? || '%'
              OR description LIKE '%' || ? || '%')
ORDER BY name, id;

-- name: search_times
SELECT id, label, moment FROM times
WHERE (? = '' OR label LIKE '%' || ? || '%')
  AND (? = '' OR substr(moment, 1, 10) = ?)
ORDER BY moment, id;

-- ГРУППА 4. Агрегатные функции (минимум два).

-- name: total_reminders
SELECT COUNT(*) AS count_reminders FROM reminders;

-- name: task_completion_totals
SELECT COUNT(*) AS total_tasks,
       COALESCE(SUM(is_completed), 0) AS completed_tasks,
       COUNT(*) - COALESCE(SUM(is_completed), 0) AS open_tasks
FROM tasks;

-- name: overview_counts
SELECT (SELECT COUNT(*) FROM reminders) AS reminder_count,
       (SELECT COUNT(*) FROM tasks) AS task_count,
       (SELECT COUNT(*) FROM categories) AS category_count,
       (SELECT COUNT(*) FROM users) AS user_count,
       (SELECT COUNT(*) FROM times) AS time_count;

-- ГРУППА 5. GROUP BY + HAVING (минимум два).

-- name: tasks_by_category
SELECT c.id, c.name, COUNT(t.id) AS task_count,
       COALESCE(SUM(t.is_completed), 0) AS done_count
FROM categories AS c
LEFT JOIN tasks AS t ON t.category_id = c.id
GROUP BY c.id, c.name ORDER BY task_count DESC, c.name;

-- name: tasks_by_user
SELECT u.id, u.name, COUNT(t.id) AS task_count,
       COALESCE(SUM(t.is_completed), 0) AS done_count
FROM users AS u
LEFT JOIN tasks AS t ON t.user_id = u.id
GROUP BY u.id, u.name ORDER BY task_count DESC, u.name;

-- name: reminders_by_category
SELECT c.id, c.name, COUNT(r.id) AS reminder_count
FROM categories AS c
LEFT JOIN reminders AS r ON r.category_id = c.id
GROUP BY c.id, c.name ORDER BY reminder_count DESC, c.name;

-- name: busy_users
SELECT u.id, u.name, COUNT(t.id) AS task_count
FROM users AS u JOIN tasks AS t ON t.user_id = u.id
GROUP BY u.id, u.name HAVING COUNT(t.id) >= ?
ORDER BY task_count DESC, u.name;

-- name: joined_reminders_for_task
SELECT r.id, r.text, r.remind_at, c.name AS category
FROM reminders AS r JOIN categories AS c ON c.id = r.category_id
WHERE r.task_id = ? ORDER BY r.remind_at, r.id;
