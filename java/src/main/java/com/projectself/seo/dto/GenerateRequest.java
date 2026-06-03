package com.projectself.seo.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class GenerateRequest {
    @NotBlank(message = "Topic is required")
    private String topic;
    
    @NotBlank(message = "Keywords are required")
    private String keywords;
    
    @NotBlank(message = "Tenant ID is required")
    private String tenantId;
    
    @NotBlank(message = "Collection name is required")
    private String collectionName;
    
    private String llmProvider = "deepseek";
    private String selectedTitle;
    private String selectedOutline;
}
