package com.projectself.seo.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI openAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("SEO RAG Gateway API")
                        .description("Java 网关：文档上传、知识库搜索、SEO 文章生成、租户管理")
                        .version("1.0.0"));
    }
}
