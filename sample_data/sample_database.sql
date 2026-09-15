-- Sample SQL dump for Data Cleaner
CREATE TABLE customers (
    id INT,
    name VARCHAR(100),
    contact VARCHAR(50),
    email VARCHAR(100),
    city VARCHAR(50),
    salary VARCHAR(50)
);

INSERT INTO customers (id, name, contact, email, city, salary) VALUES
(1, '  Rajesh Verma  ', '+91-98223-11223', 'rajesh.v@gmai.com', '  Mumbai  ', '₹65,000'),
(2, 'Snehal Patil', '9811009988', 'snehal@yaho.com', 'Pune', '55000'),
(3, 'Amit Joshi', '98abc12345', 'amit.joshi@gmail.com', 'Delhi ', 'unknown'),
(4, '  Priya Sharma', '+91 99887 66554', 'priya.s @outlook.com', 'Bengaluru', '₹78,000'),
(1, '  Rajesh Verma  ', '+91-98223-11223', 'rajesh.v@gmai.com', '  Mumbai  ', '₹65,000');
