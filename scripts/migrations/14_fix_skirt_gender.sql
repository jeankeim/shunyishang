-- 迁移14: 数据修正 - 裙装性别标注
-- 裙装不应推荐给男性用户，设为女性专属

UPDATE items SET gender = '女' WHERE category = '裙装' AND gender = '中性';
