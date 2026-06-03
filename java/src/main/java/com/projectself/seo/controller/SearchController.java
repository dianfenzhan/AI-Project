package com.projectself.seo.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.projectself.seo.service.PythonApiService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class SearchController {
    
    private final PythonApiService pythonApiService;
    
    @PostMapping("/upload")
    public ResponseEntity<JsonNode> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam("tenantId") String tenantId,
            @RequestParam("collectionName") String collectionName
    ) throws Exception {
        JsonNode result = pythonApiService.uploadDocument(file, tenantId, collectionName);
        return ResponseEntity.ok(result);
    }
    
    @PostMapping("/search")
    public ResponseEntity<JsonNode> search(
            @RequestParam("query") String query,
            @RequestParam("tenantId") String tenantId,
            @RequestParam("collectionName") String collectionName
    ) throws Exception {
        JsonNode result = pythonApiService.search(query, tenantId, collectionName);
        return ResponseEntity.ok(result);
    }
    
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

    @PostMapping("/generate/outlines")
    public ResponseEntity<JsonNode> generateOutlines(
            @RequestParam("threadId") String threadId,
            @RequestParam("selectedTitle") String selectedTitle
    ) throws Exception {
        JsonNode result = pythonApiService.generateOutlines(threadId, selectedTitle);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/generate/article")
    public ResponseEntity<JsonNode> generateArticle(
            @RequestParam("threadId") String threadId,
            @RequestParam("selectedOutline") String selectedOutline
    ) throws Exception {
        JsonNode result = pythonApiService.generateArticle(threadId, selectedOutline);
        return ResponseEntity.ok(result);
    }
}
