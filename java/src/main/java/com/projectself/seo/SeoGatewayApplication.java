package com.projectself.seo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class SeoGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(SeoGatewayApplication.class, args);
    }
}
