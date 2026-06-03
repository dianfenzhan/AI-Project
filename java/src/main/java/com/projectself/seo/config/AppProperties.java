package com.projectself.seo.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.nio.file.Path;

@ConfigurationProperties(prefix = "app")
public record AppProperties(Workflow workflow, Storage storage) {

    public record Workflow(String baseUrl) {
    }

    public record Storage(Path rootDir) {
    }
}
