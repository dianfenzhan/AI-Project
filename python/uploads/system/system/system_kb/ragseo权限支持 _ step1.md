# ragseo权限支持 | step1

# 需求

权限测支持：

seo-serivce新增SEO版本： 服务商版（全部权限），团队版（无项目授权）和协作版（只读）。

# 上线步骤

## 执行sql

库名：privilege ip:内网地址: 10.10.64.65:3306

```json
ALTER TABLE p_app_org
ADD COLUMN user_limit int NULL COMMENT '企业用户数限制（与 p_org_info.user_limit 同步，CRM 行）',
ADD COLUMN org_buy_version varchar(100) NULL COMMENT '企业购买版本',
ADD COLUMN open_date_time datetime NULL COMMENT '开通时间（闭区间起点，null 表示不限制）',
ADD COLUMN off_date_time datetime NULL COMMENT '到期时间（闭区间终点，null 表示不限制）';
```

# 部署代码

## 权限（privilege-serv）

[https://codeserv.leadscloud.com/refactorgroup/privilege/-/merge\_requests/1060](https://codeserv.leadscloud.com/refactorgroup/privilege/-/merge_requests/1060)

## ruoyi 平台(ruoyi)

[https://codeserv.leadscloud.com/refactorgroup/platform/-/merge\_requests/13](https://codeserv.leadscloud.com/refactorgroup/platform/-/merge_requests/13)