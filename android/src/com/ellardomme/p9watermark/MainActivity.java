package com.ellardomme.p9watermark;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;

import java.io.File;
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

        @JavascriptInterface
        public String saveImage(String base64, String name, String mime) {
            try {
                byte[] data = Base64.decode(base64, Base64.DEFAULT);
                File dir;
                if (Build.VERSION.SDK_INT >= 29) {
                    dir = new File(ctx.getExternalFilesDir(Environment.DIRECTORY_PICTURES), "P9水印");
                } else {
                    // Android 9 及以下：直接放在内部存储根目录，文件管理一眼能看到
                    dir = new File(Environment.getExternalStorageDirectory(), "P9水印");
                }
                if (!dir.exists()) dir.mkdirs();
                File f = new File(dir, name);
                FileOutputStream fos = new FileOutputStream(f);
                fos.write(data);
                fos.close();
                MediaScannerConnection.scanFile(ctx, new String[]{ f.getAbsolutePath() },
                        new String[]{ mime == null ? "image/jpeg" : mime }, null);
                return "ok:" + f.getAbsolutePath();
            } catch (Exception e) {
                return "err:" + e.getMessage();
            }
        }

        @JavascriptInterface
        public String saveFile(String base64, String name, String mime) {
            try {
                byte[] data = Base64.decode(base64, Base64.DEFAULT);
                File dir;
                if (Build.VERSION.SDK_INT >= 29) {
                    dir = new File(ctx.getExternalFilesDir(null), "P9水印");
                } else {
                    dir = new File(Environment.getExternalStorageDirectory(), "P9水印");
                }
                if (!dir.exists()) dir.mkdirs();
                File f = new File(dir, name);
                FileOutputStream fos = new FileOutputStream(f);
                fos.write(data);
                fos.close();
                return "ok:" + f.getAbsolutePath();
            } catch (Exception e) {
                return "err:" + e.getMessage();
            }
        }

        /* 大图分块写入：避免一次性传几十 MB 的 base64 字符串导致内存不足 */
        private File chunkFile = null;
        private FileOutputStream chunkOut = null;

        @JavascriptInterface
        public String beginSave(String name, String mime) {
            try {
                File dir;
                if (Build.VERSION.SDK_INT >= 29) {
                    dir = new File(ctx.getExternalFilesDir(Environment.DIRECTORY_PICTURES), "P9水印");
                } else {
                    dir = new File(Environment.getExternalStorageDirectory(), "P9水印");
                }
                if (!dir.exists()) dir.mkdirs();
                chunkFile = new File(dir, name);
                chunkOut = new FileOutputStream(chunkFile);
                return "ok";
            } catch (Exception e) {
                return "err:" + e.getMessage();
            }
        }

        @JavascriptInterface
        public String appendChunk(String base64) {
            try {
                if (chunkOut == null) return "err:未开始";
                byte[] data = Base64.decode(base64, Base64.DEFAULT);
                chunkOut.write(data);
                return "ok";
            } catch (Exception e) {
                return "err:" + e.getMessage();
            }
        }

        @JavascriptInterface
        public String endSave(String mime) {
            try {
                if (chunkOut == null) return "err:未开始";
                chunkOut.flush();
                chunkOut.close();
                chunkOut = null;
                MediaScannerConnection.scanFile(ctx, new String[]{ chunkFile.getAbsolutePath() },
                        new String[]{ mime == null ? "image/jpeg" : mime }, null);
                return "ok:" + chunkFile.getAbsolutePath();
            } catch (Exception e) {
                return "err:" + e.getMessage();
            } finally {
                chunkOut = null;
            }
        }

        @JavascriptInterface
        public String ping() { return "pong"; }
    }
}