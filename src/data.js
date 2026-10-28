// One data interface, two builds: the Claude artifact talks to the viewer's 「金融数据库」 connector,
// the website signs in to Supabase directly. esbuild sets __WEB__ and drops the unused side.
import * as mcp from "./data-mcp.js";
import * as web from "./data-web.js";

const impl = __WEB__ ? web : mcp;
export const call = (...a) => impl.call(...a);
export const describeError = (...a) => impl.describeError(...a);
export const fetchMeta = (...a) => impl.fetchMeta(...a);
export const fetchWeekly = (...a) => impl.fetchWeekly(...a);
export const getMcp = (...a) => impl.getMcp(...a);
export const rowsOf = (...a) => impl.rowsOf(...a);
