-- A week that is already clash-free, so the first thing you add is the
-- first thing that can go wrong. Nothing here touches 13:00-14:00.
INSERT INTO classes (day, start_min, end_min, subject, teacher, room, batch)
SELECT * FROM (VALUES
  ('mon', 540,  600,  'Database Systems',    'Prof Rao',     'A101', 'CSE-3A'),
  ('mon', 600,  660,  'Operating Systems',   'Prof Iyer',    'A101', 'CSE-3B'),
  ('mon', 660,  720,  'Computer Networks',   'Prof Nair',    'B201', 'CSE-3A'),
  ('mon', 840,  960,  'DBMS Lab',            'Prof Rao',     'LAB1', 'CSE-3A'),
  ('tue', 540,  600,  'Operating Systems',   'Prof Iyer',    'A101', 'CSE-3A'),
  ('tue', 600,  690,  'Discrete Maths',      'Prof Menon',   'A102', 'CSE-3B'),
  ('tue', 840,  900,  'Computer Networks',   'Prof Nair',    'B201', 'CSE-3B'),
  ('wed', 540,  600,  'Database Systems',    'Prof Rao',     'A101', 'CSE-3B'),
  ('wed', 630,  720,  'Software Engineering','Prof Dsouza',  'B202', 'CSE-3A'),
  ('wed', 840,  960,  'Networks Lab',        'Prof Nair',    'LAB2', 'CSE-3B'),
  ('thu', 540,  630,  'Discrete Maths',      'Prof Menon',   'A102', 'CSE-3A'),
  ('thu', 660,  720,  'Operating Systems',   'Prof Iyer',    'A101', 'CSE-3B'),
  ('thu', 840,  900,  'Software Engineering','Prof Dsouza',  'B202', 'CSE-3B'),
  ('fri', 540,  600,  'Computer Networks',   'Prof Nair',    'B201', 'CSE-3A'),
  ('fri', 600,  660,  'Database Systems',    'Prof Rao',     'A101', 'CSE-3A'),
  ('fri', 840,  960,  'OS Lab',              'Prof Iyer',    'LAB1', 'CSE-3B'),
  ('sat', 540,  660,  'Project Review',      'Prof Dsouza',  'B202', 'CSE-3A')
) AS v(day, start_min, end_min, subject, teacher, room, batch)
WHERE NOT EXISTS (SELECT 1 FROM classes);
