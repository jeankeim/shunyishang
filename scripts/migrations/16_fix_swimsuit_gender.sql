-- 迁移16: 数据修正 - 泳衣性别标注
-- ITEM_095 亮橙色泳衣（连体/露背）为女性款式，不应标记为中性

UPDATE items SET gender = '女' WHERE item_code = 'ITEM_095' AND gender = '中性';
