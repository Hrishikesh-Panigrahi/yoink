/* bridge.js — QWebChannel singleton bootstrap.
 *
 * main.js currently runs its own `new QWebChannel(...)` boot path; this
 * module exposes the same connect-once pattern via a Promise so future
 * modules can `await getBridge()` instead of registering their own
 * `onBridgeReady` callbacks.
 */

let connectPromise = null;

export function getBridge() {
  if (connectPromise) return connectPromise;
  connectPromise = new Promise((resolve, reject) => {
    if (typeof QWebChannel === "undefined" || !window.qt || !window.qt.webChannelTransport) {
      reject(new Error("QWebChannel transport not available"));
      return;
    }
    // eslint-disable-next-line no-new
    new QWebChannel(window.qt.webChannelTransport, (channel) => {
      resolve(channel.objects.bridge);
    });
  });
  return connectPromise;
}
