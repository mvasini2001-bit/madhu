use sales_intelligence_hub;

CREATE TABLE branches (
  branch_id int primary key AUTO_INCREMENT,
  branch_name varchar(100),
  branch_admin_name varchar(100)
) ;

CREATE TABLE customer_sales (
    sale_id INT PRIMARY KEY AUTO_INCREMENT,
    branch_id INT,
    date DATE,
    name VARCHAR(100),
    mobile_number VARCHAR(15),
    product_name VARCHAR(30),
    gross_sales DECIMAL(12,2),
    received_amount DECIMAL(12,2),
    pending_amount DECIMAL(12,2)GENERATED ALWAYS AS (gross_sales - received_amount) VIRTUAL,
    status ENUM('open', 'close'),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE payment_splits (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    sale_id INT,
    payment_date DATE,
    amount_paid DECIMAL(12,2),
    payment_method VARCHAR(50),
    FOREIGN KEY (sale_id) REFERENCES customer_sales(sale_id)
);

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100),
    password VARCHAR(255),
    branch_id INT,
    role ENUM('Super Admin', 'Admin'),
    email VARCHAR(255) UNIQUE,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

INSERT INTO branches (branch_id, branch_name, branch_admin_name) VALUES
(1, 'Dindigul', 'sankar'),
(2, 'Chennai', 'Madhu'),
(3, 'Madurai', 'Kavin');

SELECT * FROM branches;

INSERT INTO users (username, password, branch_id, role, email) VALUES
('Superadmin', 'YOUR_BCRYPT_HASH_1', 1, 'Super Admin', 'superadmin@example.com'),
('Admin_Chennai', 'YOUR_BCRYPT_HASH_2', 2, 'Admin', 'admin.chennai@example.com'),
('Admin_Madurai', 'YOUR_BCRYPT_HASH_3', 3, 'Admin', 'admin.madurai@example.com');

SELECT user_id, username, branch_id, role, email FROM users;

INSERT INTO customer_sales (branch_id, date, name, mobile_number,product_name, gross_sales, received_amount, status) VALUES
(1, 1,2026-09-28, Madhu, 7208793103,Laptop, 50000, 17000, open),
(2, 2, 2026-09-28, Madhu, 7208793103,Laptop, 50000, 0, open),
(3, 3, 2026-09-28, Madhu,7208793103,Laptop, 50000, 2000, open),
(4, 2, 2026-09-28, Madhu, 7208793103,Laptop, 50000, 0, open),
(13, 3, 2026-11-02, Ravi, 9876543210,DS, 10000, 0, open),
(19, 3, 2026-11-02, Ravi, 9876543210,DS, 10000, 0, open);
SELECT *FROM customer_sales ORDER BY sale_id;

INSERT INTO payment_splits (sale_id, payment_date, amount_paid, payment_method) VALUES
(1, 1, 2026-10-26, 10000, UPI),
(2, 1, 2026-10-26, 5000, Cash),
(5, 1, 2026-10-26, 2000, UPI),
(6, 3, 2026-11-02, 1000, Cash),
(7, 3, 2026-11-02, 1000, Cash);

SELECT *FROM payment_splits ORDER BY payment_id;

select*from users where email="superadmin@example.com";

select*from customer_sales;
select*from branches;
select*from payment_splits;
select*from customer_sales where status="open";
select*from customer_sales cs join branches b on cs.branch_id=b.branch_id where b.branch_name="Chennai";

select sum(gross_sales) as total_gross_sales from customer_sales;
select sum(received_amount) as total_received_amount from customer_sales;
select sum(pending_amount) as total_pending_amount from customer_sales;
select  b.branch_name,count(cs.sale_id) as total_number_of_sales from branches b join customer_sales cs on b.branch_id=cs.branch_id group by b.branch_name;
select avg(gross_sales) from customer_sales;

select cs.*,b.branch_name from customer_sales cs join branches b on cs.branch_id=b.branch_id;
select cs.sale_id,cs.product_name,cs.gross_sales,sum(ps.amount_paid) as total_payment_received from customer_sales cs 
join payment_splits ps on ps.sale_id=cs.sale_id group by  cs.sale_id,cs.product_name,cs.gross_sales;
select b.branch_name,sum(cs.gross_sales) as total_gross_sale from customer_sales cs join branches b on cs.branch_id=b.branch_id group by b.branch_name;
select cs.*, ps.payment_method from payment_splits ps join customer_sales cs on ps.sale_id=cs.sale_id;
select cs.*,b.branch_admin_name from customer_sales cs join branches b on cs.branch_id=b.branch_id;

select*from customer_sales where pending_amount>5000;
select*from customer_sales order by gross_sales desc limit 3;
select b.branch_name,sum(cs.gross_sales) as total_gross_sales from customer_sales cs join branches b 
on b.branch_id=cs.branch_id group by b.branch_name order by total_gross_sales desc limit 1;
select payment_method,sum(amount_paid) as total_collection from payment_splits group by payment_method;