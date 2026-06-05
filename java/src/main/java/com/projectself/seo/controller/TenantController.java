package com.projectself.seo.controller;

import com.projectself.seo.dto.CreateTenantRequest;
import com.projectself.seo.entity.Tenant;
import com.projectself.seo.repository.TenantRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/tenants")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
@Tag(name = "租户管理", description = "租户 CRUD")
public class TenantController {
    
    private final TenantRepository tenantRepository;
    
    @Operation(summary = "获取所有租户")
    @GetMapping
    public ResponseEntity<List<Tenant>> getAllTenants() {
        return ResponseEntity.ok(tenantRepository.findAll());
    }
    
    @Operation(summary = "获取单个租户")
    @GetMapping("/{tenantId}")
    public ResponseEntity<Tenant> getTenant(@PathVariable String tenantId) {
        return tenantRepository.findByTenantId(tenantId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
    
    @Operation(summary = "创建租户")
    @PostMapping
    public ResponseEntity<Tenant> createTenant(@Valid @RequestBody CreateTenantRequest request) {
        if (tenantRepository.existsByTenantId(request.getTenantId())) {
            return ResponseEntity.badRequest().build();
        }
        
        Tenant tenant = new Tenant();
        tenant.setTenantId(request.getTenantId());
        tenant.setName(request.getName());
        tenant.setCollectionName(request.getCollectionName());
        tenant.setDefaultLlmProvider(request.getDefaultLlmProvider());
        
        return ResponseEntity.ok(tenantRepository.save(tenant));
    }
}
