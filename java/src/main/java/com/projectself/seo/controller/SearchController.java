package com.projectself.seo.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.projectself.seo.service.PythonApiService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
@Tag(name = "RAG & 文章生成", description = "文档上传、知识库搜索、三步 SEO 文章生成")
public class SearchController {
    
    private final PythonApiService pythonApiService;
    
    @Operation(summary = "上传文档", description = "上传 PDF/MD/TXT/DOCX 并索引到 Milvus 与 Elasticsearch；scope=tenant 租户级，scope=system 系统级共享")
    @PostMapping("/upload")
    public ResponseEntity<JsonNode> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam("tenantId") String tenantId,
            @RequestParam("collectionName") String collectionName,
            @RequestParam(value = "scope", defaultValue = "tenant") String scope
    ) throws Exception {
        JsonNode result = pythonApiService.uploadDocument(file, tenantId, collectionName, scope);
        return ResponseEntity.ok(result);
    }
    
    @Operation(summary = "搜索知识库", description = "双路召回 + 重排序，返回 Top-K 结果")
    @PostMapping("/search")
    public ResponseEntity<JsonNode> search(
            @RequestParam("query") String query,
            @RequestParam("tenantId") String tenantId,
            @RequestParam("collectionName") String collectionName
    ) throws Exception {
        JsonNode result = pythonApiService.search(query, tenantId, collectionName);
        return ResponseEntity.ok(result);
    }
    
    @Operation(summary = "生成标题", description = "第一步：基于 RAG + SerpAPI 生成 5 个标题")
    @PostMapping("/generate/titles")
    public ResponseEntity<JsonNode> generateTitles(
            @RequestParam("topic") String topic,
            @RequestParam("keywords") String keywords,
            @RequestParam("tenantId") String tenantId,
            @RequestParam("collectionName") String collectionName,
            @RequestParam(value = "llmProvider", defaultValue = "deepseek") String llmProvider
    ) throws Exception {
        JsonNode result = pythonApiService.generateTitles(topic, keywords, tenantId, collectionName, llmProvider);
        return ResponseEntity.ok(result);
    }

    @Operation(summary = "生成大纲", description = "第二步：根据选定标题生成 3 套大纲")
    @PostMapping("/generate/outlines")
    public ResponseEntity<JsonNode> generateOutlines(
            @RequestParam("threadId") String threadId,
            @RequestParam("selectedTitle") String selectedTitle
    ) throws Exception {
        JsonNode result = pythonApiService.generateOutlines(threadId, selectedTitle);
        return ResponseEntity.ok(result);
    }

    @Operation(summary = "生成文章", description = "第三步：根据选定大纲生成完整 SEO 文章")
    @PostMapping("/generate/article")
    public ResponseEntity<JsonNode> generateArticle(
            @RequestParam("threadId") String threadId,
            @RequestParam("selectedOutline") String selectedOutline
    ) throws Exception {
        JsonNode result = pythonApiService.generateArticle(threadId, selectedOutline);
        return ResponseEntity.ok(result);
    }
}
