package com.ellardomme.p9watermark;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.ContentValues;
import android.media.MediaScannerConnection;
import android.provider.MediaStore;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.ParcelFileDescriptor;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;

import java.io.File;
import java.io.OutputStream;
import java.io.FileOutputStream;

public class MainActivity extends Activity {
    private static final int REQ_FILE = 1001;
    private WebView web;
    private ValueCallback<Uri[]> filePathCallback;
    private long lastBackPress = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setTextZoom(100);
        web.setBackgroundColor(0xff0a0a0c);
        web.addJavascriptInterface(new Bridge(this), "AndroidBridge");

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> cb, FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = cb;
                try {
                    Intent it = new Intent(Intent.ACTION_GET_CONTENT);
                    it.addCategory(Intent.CATEGORY_OPENABLE);
                    // 按页面声明的 accept 决定文件类型：导入预设时要能选 json
                    String[] accepts = params.getAcceptTypes();
                    boolean allowAny = false;
                    if (accepts != null) {
                        for (String a : accepts) {
                            if (a == null) continue;
                            String l = a.toLowerCase();
                            if (l.contains("json") || l.contains("application")) { allowAny = true; break; }
                        }
                    }
                    it.setType(allowAny ? "*/*" : "image/*");
                    startActivityForResult(Intent.createChooser(it, "选择照片"), REQ_FILE);
                    return true;
                } catch (Exception e) {
                    filePathCallback = null;
                    return false;
                }
            }
        });

        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");

        if (Build.VERSION.SDK_INT >= 23 &&
                checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{ Manifest.permission.WRITE_EXTERNAL_STORAGE }, 1);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQ_FILE) {
            Uri[] result = null;
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                result = new Uri[]{ data.getData() };
            }
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(result);
                filePathCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onBackPressed() {
        if (web == null) {
            super.onBackPressed();
            return;
        }
        web.evaluateJavascript(
            "(function(){try{return !!(window.__onBack && window.__onBack());}catch(e){return false;}})()",
            new ValueCallback<String>() {
                @Override
                public void onReceiveValue(String value) {
                    if ("true".equals(value)) {
                        return;
                    }
                    long now = System.currentTimeMillis();
                    if (now - lastBackPress < 2000) {
                        finish();
                    } else {
                        lastBackPress = now;
                        Toast.makeText(MainActivity.this, "再按一次退出", Toast.LENGTH_SHORT).show();
                    }
                }
            });
    }

    public static class Bridge {
        private final Context ctx;
        Bridge(Context c) { ctx = c; }

        /* ---------- 统一的写入通道：Q+ 走 MediaStore（相册可见），旧系统写文件 ---------- */
        private Uri pendingUri = null;
        private OutputStream out = null;

        private OutputStream openStream(String name, String mime) throws Exception {
            if (Build.VERSION.SDK_INT >= 29) {
                ContentValues cv = new ContentValues();
                cv.put(MediaStore.Images.Media.DISPLAY_NAME, name);
                cv.put(MediaStore.Images.Media.MIME_TYPE, mime == null ? "image/jpeg" : mime);
                cv.put(MediaStore.Images.Media.RELATIVE_PATH,
                        Environment.DIRECTORY_PICTURES + "/德味水印");
                cv.put(MediaStore.Images.Media.IS_PENDING, 1);
                pendingUri = ctx.getContentResolver().insert(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI, cv);
                if (pendingUri == null) throw new Exception("无法创建相册条目");
                return ctx.getContentResolver().openOutputStream(pendingUri);
            }
            File dir = new File(Environment.getExternalStorageDirectory(), "德味水印");
            if (!dir.exists()) dir.mkdirs();
            File f = new File(dir, name);
            pendingUri = Uri.fromFile(f);
            return new FileOutputStream(f);
        }

        private String finishStream(String mime) {
            try {
                if (out != null) { out.flush(); out.close(); out = null; }
                if (pendingUri == null) return "err:未开始";
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues cv = new ContentValues();
                    cv.put(MediaStore.Images.Media.IS_PENDING, 0);
                    ctx.getContentResolver().update(pendingUri, cv, null, null);
                } else {
                    MediaScannerConnection.scanFile(ctx,
                            new String[]{ pendingUri.getPath() },
                            new String[]{ mime == null ? "image/jpeg" : mime }, null);
                }
                return "ok:" + pendingUri;
            } catch (Exception e) {
                return "err:" + e.getMessage();
            } finally {
                pendingUri = null;
            }
        }

        @JavascriptInterface
        public String saveImage(String base64, String name, String mime) {
            try {
                byte[] data = Base64.decode(base64, Base64.DEFAULT);
                out = openStream(name, mime);
                out.write(data);
                return finishStream(mime);
            } catch (Exception e) {
                return "err:" + e.getMessage();
            } finally {
                try { if (out != null) { out.close(); out = null; } } catch (Exception ignore) {}
            }
        }

        @JavascriptInterface
        public String saveFile(String base64, String name, String mime) {
            return saveImage(base64, name, mime);
        }

        /* ---------- 大图分块写入 ---------- */
        @JavascriptInterface
        public String beginSave(String name, String mime) {
            try {
                out = openStream(name, mime);
                return "ok";
            } catch (Exception e) {
                return "err:" + e.getMessage();
            }
        }

        @JavascriptInterface
        public String appendChunk(String base64) {
            try {
                if (out == null) return "err:未开始";
                out.write(Base64.decode(base64, Base64.DEFAULT));
                return "ok";
            } catch (Exception e) {
                return "err:" + e.getMessage();
            }
        }

        @JavascriptInterface
        public String endSave(String mime) {
            return finishStream(mime);
        }

        @JavascriptInterface
        public String ping() { return "pong"; }
    }
}