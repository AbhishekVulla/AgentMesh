import * as vscode from "vscode";
import * as fs from "node:fs";
import { EventSource } from "./ws_client";
import type { AgentMeshEvent } from "./types/events";

class OverlayProvider implements vscode.WebviewViewProvider {
  public view?: vscode.WebviewView;
  private pending: AgentMeshEvent[] = [];

  constructor(
    private readonly ctx: vscode.ExtensionContext,
    source: EventSource,
  ) {
    source.onEvent((evt) => this.forward(evt));
  }

  private forward(evt: AgentMeshEvent) {
    if (this.view) {
      this.view.webview.postMessage({ kind: "event", evt });
    } else {
      this.pending.push(evt);
    }
  }

  resolveWebviewView(webviewView: vscode.WebviewView): void | Thenable<void> {
    this.view = webviewView;
    const distRoot = vscode.Uri.joinPath(this.ctx.extensionUri, "webview-ui", "dist");
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [distRoot],
    };
    webviewView.webview.html = this.getHtml(webviewView.webview);

    // Flush pending events that arrived before the view was created.
    for (const evt of this.pending) {
      webviewView.webview.postMessage({ kind: "event", evt });
    }
    this.pending = [];
  }

  private getHtml(webview: vscode.Webview): string {
    const distRoot = vscode.Uri.joinPath(this.ctx.extensionUri, "webview-ui", "dist");
    const indexFs = vscode.Uri.joinPath(distRoot, "index.html").fsPath;

    if (!fs.existsSync(indexFs)) {
      return /* html */ `
        <!doctype html>
        <html>
          <body style="font-family: var(--vscode-font-family); padding: 16px;">
            <h3>AgentMesh overlay not built yet</h3>
            <p>Run <code>npm run build</code> inside <code>extension/</code> first, then reload the VS Code window.</p>
          </body>
        </html>
      `;
    }

    let html = fs.readFileSync(indexFs, "utf-8");
    // Rewrite relative asset paths (either "/foo" or "./foo") to webview URIs.
    // Vite emits "./assets/..." by default; leave absolute http(s):// alone.
    html = html.replace(
      /(src|href)="(?!https?:|data:|vscode-webview:)(?:\.\/|\/)?([^"]+)"/g,
      (_m, attr, p) => {
        const uri = webview.asWebviewUri(vscode.Uri.joinPath(distRoot, p));
        return `${attr}="${uri}"`;
      },
    );
    // Tighten CSP.
    const cspSource = webview.cspSource;
    const csp = [
      "default-src 'none'",
      `img-src ${cspSource} data:`,
      `style-src ${cspSource} 'unsafe-inline'`,
      `script-src ${cspSource}`,
      `font-src ${cspSource}`,
      `connect-src ${cspSource}`,
    ].join("; ");
    if (!/Content-Security-Policy/i.test(html)) {
      html = html.replace(
        "<head>",
        `<head><meta http-equiv="Content-Security-Policy" content="${csp}">`,
      );
    }
    return html;
  }
}

export function activate(ctx: vscode.ExtensionContext): void {
  const source = new EventSource(ctx);
  const provider = new OverlayProvider(ctx, source);

  ctx.subscriptions.push(
    vscode.window.registerWebviewViewProvider("agentmesh.overlay", provider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
  );

  ctx.subscriptions.push(
    vscode.commands.registerCommand("agentmesh.reconnect", async () => {
      source.stop();
      await source.start();
      vscode.window.showInformationMessage("AgentMesh: reconnecting");
    }),
  );

  ctx.subscriptions.push(
    vscode.commands.registerCommand("agentmesh.toggleSource", async () => {
      const cfg = vscode.workspace.getConfiguration("agentmesh");
      const cur = cfg.get<string>("source", "auto");
      const next = cur === "auto" ? "live" : cur === "live" ? "mock" : "auto";
      await cfg.update("source", next, vscode.ConfigurationTarget.Workspace);
      source.stop();
      await source.start();
      vscode.window.showInformationMessage(`AgentMesh source: ${next}`);
    }),
  );

  ctx.subscriptions.push({ dispose: () => source.dispose() });

  void source.start();
}

export function deactivate(): void {
  /* registered disposables are cleaned up by VS Code */
}
