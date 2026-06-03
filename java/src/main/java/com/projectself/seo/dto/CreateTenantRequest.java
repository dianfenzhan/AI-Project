package com.projectself.seo.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateTenantRequest {
    @NotBlank(message = "Tenant ID is required")
    private String tenantId;
    
    @NotBlank(message = "Name is required")
    private String name;
    
    @NotBlank(message = "Collection name is required")
    private String collectionName;
    
    private String defaultLlmProvider = "deepseek";
}
