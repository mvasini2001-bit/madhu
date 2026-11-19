use sales_intelligence_hub;

DELIMITER //
CREATE TRIGGER after_payment_insert
 AFTER INSERT ON payment_splits
 FOR EACH ROW begin
 update customer_sales
 set received_amount=(
 select sum(amount_paid)
 from payment_splits
 where sale_id=new.sale_id
 )
where sale_id=new.sale_id;
END //
DELIMITER ;

