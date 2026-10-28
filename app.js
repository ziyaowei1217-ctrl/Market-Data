(()=>{var tk=Object.create;var Od=Object.defineProperty;var nk=Object.getOwnPropertyDescriptor;var rk=Object.getOwnPropertyNames;var ok=Object.getPrototypeOf,ak=Object.prototype.hasOwnProperty;var wn=(e,t)=>()=>(t||e((t={exports:{}}).exports,t),t.exports),lk=(e,t)=>{for(var n in t)Od(e,n,{get:t[n],enumerable:!0})},ik=(e,t,n,r)=>{if(t&&typeof t=="object"||typeof t=="function")for(let o of rk(t))!ak.call(e,o)&&o!==n&&Od(e,o,{get:()=>t[o],enumerable:!(r=nk(t,o))||r.enumerable});return e};var w=(e,t,n)=>(n=e!=null?tk(ok(e)):{},ik(t||!e||!e.__esModule?Od(n,"default",{value:e,enumerable:!0}):n,e));var lh=wn(Ce=>{"use strict";var Pl=Symbol.for("react.element"),sk=Symbol.for("react.portal"),ck=Symbol.for("react.fragment"),uk=Symbol.for("react.strict_mode"),dk=Symbol.for("react.profiler"),fk=Symbol.for("react.provider"),pk=Symbol.for("react.context"),mk=Symbol.for("react.forward_ref"),vk=Symbol.for("react.suspense"),gk=Symbol.for("react.memo"),hk=Symbol.for("react.lazy"),Yg=Symbol.iterator;function bk(e){return e===null||typeof e!="object"?null:(e=Yg&&e[Yg]||e["@@iterator"],typeof e=="function"?e:null)}var Zg={isMounted:function(){return!1},enqueueForceUpdate:function(){},enqueueReplaceState:function(){},enqueueSetState:function(){}},Jg=Object.assign,eh={};function ma(e,t,n){this.props=e,this.context=t,this.refs=eh,this.updater=n||Zg}ma.prototype.isReactComponent={};ma.prototype.setState=function(e,t){if(typeof e!="object"&&typeof e!="function"&&e!=null)throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");this.updater.enqueueSetState(this,e,t,"setState")};ma.prototype.forceUpdate=function(e){this.updater.enqueueForceUpdate(this,e,"forceUpdate")};function th(){}th.prototype=ma.prototype;function Bd(e,t,n){this.props=e,this.context=t,this.refs=eh,this.updater=n||Zg}var Ad=Bd.prototype=new th;Ad.constructor=Bd;Jg(Ad,ma.prototype);Ad.isPureReactComponent=!0;var Qg=Array.isArray,nh=Object.prototype.hasOwnProperty,Fd={current:null},rh={key:!0,ref:!0,__self:!0,__source:!0};function oh(e,t,n){var r,o={},a=null,l=null;if(t!=null)for(r in t.ref!==void 0&&(l=t.ref),t.key!==void 0&&(a=""+t.key),t)nh.call(t,r)&&!rh.hasOwnProperty(r)&&(o[r]=t[r]);var i=arguments.length-2;if(i===1)o.children=n;else if(1<i){for(var s=Array(i),c=0;c<i;c++)s[c]=arguments[c+2];o.children=s}if(e&&e.defaultProps)for(r in i=e.defaultProps,i)o[r]===void 0&&(o[r]=i[r]);return{$$typeof:Pl,type:e,key:a,ref:l,props:o,_owner:Fd.current}}function xk(e,t){return{$$typeof:Pl,type:e.type,key:t,ref:e.ref,props:e.props,_owner:e._owner}}function Md(e){return typeof e=="object"&&e!==null&&e.$$typeof===Pl}function yk(e){var t={"=":"=0",":":"=2"};return"$"+e.replace(/[=:]/g,function(n){return t[n]})}var Xg=/\/+/g;function Nd(e,t){return typeof e=="object"&&e!==null&&e.key!=null?yk(""+e.key):t.toString(36)}function ws(e,t,n,r,o){var a=typeof e;(a==="undefined"||a==="boolean")&&(e=null);var l=!1;if(e===null)l=!0;else switch(a){case"string":case"number":l=!0;break;case"object":switch(e.$$typeof){case Pl:case sk:l=!0}}if(l)return l=e,o=o(l),e=r===""?"."+Nd(l,0):r,Qg(o)?(n="",e!=null&&(n=e.replace(Xg,"$&/")+"/"),ws(o,t,n,"",function(c){return c})):o!=null&&(Md(o)&&(o=xk(o,n+(!o.key||l&&l.key===o.key?"":(""+o.key).replace(Xg,"$&/")+"/")+e)),t.push(o)),1;if(l=0,r=r===""?".":r+":",Qg(e))for(var i=0;i<e.length;i++){a=e[i];var s=r+Nd(a,i);l+=ws(a,t,n,s,o)}else if(s=bk(e),typeof s=="function")for(e=s.call(e),i=0;!(a=e.next()).done;)a=a.value,s=r+Nd(a,i++),l+=ws(a,t,n,s,o);else if(a==="object")throw t=String(e),Error("Objects are not valid as a React child (found: "+(t==="[object Object]"?"object with keys {"+Object.keys(e).join(", ")+"}":t)+"). If you meant to render a collection of children, use an array instead.");return l}function ys(e,t,n){if(e==null)return e;var r=[],o=0;return ws(e,r,"","",function(a){return t.call(n,a,o++)}),r}function wk(e){if(e._status===-1){var t=e._result;t=t(),t.then(function(n){(e._status===0||e._status===-1)&&(e._status=1,e._result=n)},function(n){(e._status===0||e._status===-1)&&(e._status=2,e._result=n)}),e._status===-1&&(e._status=0,e._result=t)}if(e._status===1)return e._result.default;throw e._result}var Et={current:null},Is={transition:null},Ik={ReactCurrentDispatcher:Et,ReactCurrentBatchConfig:Is,ReactCurrentOwner:Fd};function ah(){throw Error("act(...) is not supported in production builds of React.")}Ce.Children={map:ys,forEach:function(e,t,n){ys(e,function(){t.apply(this,arguments)},n)},count:function(e){var t=0;return ys(e,function(){t++}),t},toArray:function(e){return ys(e,function(t){return t})||[]},only:function(e){if(!Md(e))throw Error("React.Children.only expected to receive a single React element child.");return e}};Ce.Component=ma;Ce.Fragment=ck;Ce.Profiler=dk;Ce.PureComponent=Bd;Ce.StrictMode=uk;Ce.Suspense=vk;Ce.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=Ik;Ce.act=ah;Ce.cloneElement=function(e,t,n){if(e==null)throw Error("React.cloneElement(...): The argument must be a React element, but you passed "+e+".");var r=Jg({},e.props),o=e.key,a=e.ref,l=e._owner;if(t!=null){if(t.ref!==void 0&&(a=t.ref,l=Fd.current),t.key!==void 0&&(o=""+t.key),e.type&&e.type.defaultProps)var i=e.type.defaultProps;for(s in t)nh.call(t,s)&&!rh.hasOwnProperty(s)&&(r[s]=t[s]===void 0&&i!==void 0?i[s]:t[s])}var s=arguments.length-2;if(s===1)r.children=n;else if(1<s){i=Array(s);for(var c=0;c<s;c++)i[c]=arguments[c+2];r.children=i}return{$$typeof:Pl,type:e.type,key:o,ref:a,props:r,_owner:l}};Ce.createContext=function(e){return e={$$typeof:pk,_currentValue:e,_currentValue2:e,_threadCount:0,Provider:null,Consumer:null,_defaultValue:null,_globalName:null},e.Provider={$$typeof:fk,_context:e},e.Consumer=e};Ce.createElement=oh;Ce.createFactory=function(e){var t=oh.bind(null,e);return t.type=e,t};Ce.createRef=function(){return{current:null}};Ce.forwardRef=function(e){return{$$typeof:mk,render:e}};Ce.isValidElement=Md;Ce.lazy=function(e){return{$$typeof:hk,_payload:{_status:-1,_result:e},_init:wk}};Ce.memo=function(e,t){return{$$typeof:gk,type:e,compare:t===void 0?null:t}};Ce.startTransition=function(e){var t=Is.transition;Is.transition={};try{e()}finally{Is.transition=t}};Ce.unstable_act=ah;Ce.useCallback=function(e,t){return Et.current.useCallback(e,t)};Ce.useContext=function(e){return Et.current.useContext(e)};Ce.useDebugValue=function(){};Ce.useDeferredValue=function(e){return Et.current.useDeferredValue(e)};Ce.useEffect=function(e,t){return Et.current.useEffect(e,t)};Ce.useId=function(){return Et.current.useId()};Ce.useImperativeHandle=function(e,t,n){return Et.current.useImperativeHandle(e,t,n)};Ce.useInsertionEffect=function(e,t){return Et.current.useInsertionEffect(e,t)};Ce.useLayoutEffect=function(e,t){return Et.current.useLayoutEffect(e,t)};Ce.useMemo=function(e,t){return Et.current.useMemo(e,t)};Ce.useReducer=function(e,t,n){return Et.current.useReducer(e,t,n)};Ce.useRef=function(e){return Et.current.useRef(e)};Ce.useState=function(e){return Et.current.useState(e)};Ce.useSyncExternalStore=function(e,t,n){return Et.current.useSyncExternalStore(e,t,n)};Ce.useTransition=function(){return Et.current.useTransition()};Ce.version="18.3.1"});var E=wn((B2,ih)=>{"use strict";ih.exports=lh()});var hh=wn(Ne=>{"use strict";function jd(e,t){var n=e.length;e.push(t);e:for(;0<n;){var r=n-1>>>1,o=e[r];if(0<Cs(o,t))e[r]=t,e[n]=o,n=r;else break e}}function In(e){return e.length===0?null:e[0]}function ks(e){if(e.length===0)return null;var t=e[0],n=e.pop();if(n!==t){e[0]=n;e:for(var r=0,o=e.length,a=o>>>1;r<a;){var l=2*(r+1)-1,i=e[l],s=l+1,c=e[s];if(0>Cs(i,n))s<o&&0>Cs(c,i)?(e[r]=c,e[s]=n,r=s):(e[r]=i,e[l]=n,r=l);else if(s<o&&0>Cs(c,n))e[r]=c,e[s]=n,r=s;else break e}}return t}function Cs(e,t){var n=e.sortIndex-t.sortIndex;return n!==0?n:e.id-t.id}typeof performance=="object"&&typeof performance.now=="function"?(sh=performance,Ne.unstable_now=function(){return sh.now()}):(Dd=Date,ch=Dd.now(),Ne.unstable_now=function(){return Dd.now()-ch});var sh,Dd,ch,Un=[],Wr=[],Ck=1,ln=null,ht=3,Ts=!1,No=!1,Ll=!1,fh=typeof setTimeout=="function"?setTimeout:null,ph=typeof clearTimeout=="function"?clearTimeout:null,uh=typeof setImmediate<"u"?setImmediate:null;typeof navigator<"u"&&navigator.scheduling!==void 0&&navigator.scheduling.isInputPending!==void 0&&navigator.scheduling.isInputPending.bind(navigator.scheduling);function Vd(e){for(var t=In(Wr);t!==null;){if(t.callback===null)ks(Wr);else if(t.startTime<=e)ks(Wr),t.sortIndex=t.expirationTime,jd(Un,t);else break;t=In(Wr)}}function Hd(e){if(Ll=!1,Vd(e),!No)if(In(Un)!==null)No=!0,Ud($d);else{var t=In(Wr);t!==null&&Kd(Hd,t.startTime-e)}}function $d(e,t){No=!1,Ll&&(Ll=!1,ph(Ol),Ol=-1),Ts=!0;var n=ht;try{for(Vd(t),ln=In(Un);ln!==null&&(!(ln.expirationTime>t)||e&&!gh());){var r=ln.callback;if(typeof r=="function"){ln.callback=null,ht=ln.priorityLevel;var o=r(ln.expirationTime<=t);t=Ne.unstable_now(),typeof o=="function"?ln.callback=o:ln===In(Un)&&ks(Un),Vd(t)}else ks(Un);ln=In(Un)}if(ln!==null)var a=!0;else{var l=In(Wr);l!==null&&Kd(Hd,l.startTime-t),a=!1}return a}finally{ln=null,ht=n,Ts=!1}}var Rs=!1,Ss=null,Ol=-1,mh=5,vh=-1;function gh(){return!(Ne.unstable_now()-vh<mh)}function zd(){if(Ss!==null){var e=Ne.unstable_now();vh=e;var t=!0;try{t=Ss(!0,e)}finally{t?_l():(Rs=!1,Ss=null)}}else Rs=!1}var _l;typeof uh=="function"?_l=function(){uh(zd)}:typeof MessageChannel<"u"?(Wd=new MessageChannel,dh=Wd.port2,Wd.port1.onmessage=zd,_l=function(){dh.postMessage(null)}):_l=function(){fh(zd,0)};var Wd,dh;function Ud(e){Ss=e,Rs||(Rs=!0,_l())}function Kd(e,t){Ol=fh(function(){e(Ne.unstable_now())},t)}Ne.unstable_IdlePriority=5;Ne.unstable_ImmediatePriority=1;Ne.unstable_LowPriority=4;Ne.unstable_NormalPriority=3;Ne.unstable_Profiling=null;Ne.unstable_UserBlockingPriority=2;Ne.unstable_cancelCallback=function(e){e.callback=null};Ne.unstable_continueExecution=function(){No||Ts||(No=!0,Ud($d))};Ne.unstable_forceFrameRate=function(e){0>e||125<e?console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"):mh=0<e?Math.floor(1e3/e):5};Ne.unstable_getCurrentPriorityLevel=function(){return ht};Ne.unstable_getFirstCallbackNode=function(){return In(Un)};Ne.unstable_next=function(e){switch(ht){case 1:case 2:case 3:var t=3;break;default:t=ht}var n=ht;ht=t;try{return e()}finally{ht=n}};Ne.unstable_pauseExecution=function(){};Ne.unstable_requestPaint=function(){};Ne.unstable_runWithPriority=function(e,t){switch(e){case 1:case 2:case 3:case 4:case 5:break;default:e=3}var n=ht;ht=e;try{return t()}finally{ht=n}};Ne.unstable_scheduleCallback=function(e,t,n){var r=Ne.unstable_now();switch(typeof n=="object"&&n!==null?(n=n.delay,n=typeof n=="number"&&0<n?r+n:r):n=r,e){case 1:var o=-1;break;case 2:o=250;break;case 5:o=1073741823;break;case 4:o=1e4;break;default:o=5e3}return o=n+o,e={id:Ck++,callback:t,priorityLevel:e,startTime:n,expirationTime:o,sortIndex:-1},n>r?(e.sortIndex=n,jd(Wr,e),In(Un)===null&&e===In(Wr)&&(Ll?(ph(Ol),Ol=-1):Ll=!0,Kd(Hd,n-r))):(e.sortIndex=o,jd(Un,e),No||Ts||(No=!0,Ud($d))),e};Ne.unstable_shouldYield=gh;Ne.unstable_wrapCallback=function(e){var t=ht;return function(){var n=ht;ht=t;try{return e.apply(this,arguments)}finally{ht=n}}}});var xh=wn((F2,bh)=>{"use strict";bh.exports=hh()});var Cy=wn(Yt=>{"use strict";var Sk=E(),Gt=xh();function H(e){for(var t="https://reactjs.org/docs/error-decoder.html?invariant="+e,n=1;n<arguments.length;n++)t+="&args[]="+encodeURIComponent(arguments[n]);return"Minified React error #"+e+"; visit "+t+" for the full message or use the non-minified dev environment for full errors and additional helpful warnings."}var Tb=new Set,ei={};function Ko(e,t){Aa(e,t),Aa(e+"Capture",t)}function Aa(e,t){for(ei[e]=t,e=0;e<t.length;e++)Tb.add(t[e])}var br=!(typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"),gf=Object.prototype.hasOwnProperty,kk=/^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,yh={},wh={};function Tk(e){return gf.call(wh,e)?!0:gf.call(yh,e)?!1:kk.test(e)?wh[e]=!0:(yh[e]=!0,!1)}function Rk(e,t,n,r){if(n!==null&&n.type===0)return!1;switch(typeof t){case"function":case"symbol":return!0;case"boolean":return r?!1:n!==null?!n.acceptsBooleans:(e=e.toLowerCase().slice(0,5),e!=="data-"&&e!=="aria-");default:return!1}}function Ek(e,t,n,r){if(t===null||typeof t>"u"||Rk(e,t,n,r))return!0;if(r)return!1;if(n!==null)switch(n.type){case 3:return!t;case 4:return t===!1;case 5:return isNaN(t);case 6:return isNaN(t)||1>t}return!1}function Lt(e,t,n,r,o,a,l){this.acceptsBooleans=t===2||t===3||t===4,this.attributeName=r,this.attributeNamespace=o,this.mustUseProperty=n,this.propertyName=e,this.type=t,this.sanitizeURL=a,this.removeEmptyString=l}var pt={};"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(e){pt[e]=new Lt(e,0,!1,e,null,!1,!1)});[["acceptCharset","accept-charset"],["className","class"],["htmlFor","for"],["httpEquiv","http-equiv"]].forEach(function(e){var t=e[0];pt[t]=new Lt(t,1,!1,e[1],null,!1,!1)});["contentEditable","draggable","spellCheck","value"].forEach(function(e){pt[e]=new Lt(e,2,!1,e.toLowerCase(),null,!1,!1)});["autoReverse","externalResourcesRequired","focusable","preserveAlpha"].forEach(function(e){pt[e]=new Lt(e,2,!1,e,null,!1,!1)});"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(e){pt[e]=new Lt(e,3,!1,e.toLowerCase(),null,!1,!1)});["checked","multiple","muted","selected"].forEach(function(e){pt[e]=new Lt(e,3,!0,e,null,!1,!1)});["capture","download"].forEach(function(e){pt[e]=new Lt(e,4,!1,e,null,!1,!1)});["cols","rows","size","span"].forEach(function(e){pt[e]=new Lt(e,6,!1,e,null,!1,!1)});["rowSpan","start"].forEach(function(e){pt[e]=new Lt(e,5,!1,e.toLowerCase(),null,!1,!1)});var sp=/[\-:]([a-z])/g;function cp(e){return e[1].toUpperCase()}"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(e){var t=e.replace(sp,cp);pt[t]=new Lt(t,1,!1,e,null,!1,!1)});"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(e){var t=e.replace(sp,cp);pt[t]=new Lt(t,1,!1,e,"http://www.w3.org/1999/xlink",!1,!1)});["xml:base","xml:lang","xml:space"].forEach(function(e){var t=e.replace(sp,cp);pt[t]=new Lt(t,1,!1,e,"http://www.w3.org/XML/1998/namespace",!1,!1)});["tabIndex","crossOrigin"].forEach(function(e){pt[e]=new Lt(e,1,!1,e.toLowerCase(),null,!1,!1)});pt.xlinkHref=new Lt("xlinkHref",1,!1,"xlink:href","http://www.w3.org/1999/xlink",!0,!1);["src","href","action","formAction"].forEach(function(e){pt[e]=new Lt(e,1,!1,e.toLowerCase(),null,!0,!0)});function up(e,t,n,r){var o=pt.hasOwnProperty(t)?pt[t]:null;(o!==null?o.type!==0:r||!(2<t.length)||t[0]!=="o"&&t[0]!=="O"||t[1]!=="n"&&t[1]!=="N")&&(Ek(t,n,o,r)&&(n=null),r||o===null?Tk(t)&&(n===null?e.removeAttribute(t):e.setAttribute(t,""+n)):o.mustUseProperty?e[o.propertyName]=n===null?o.type===3?!1:"":n:(t=o.attributeName,r=o.attributeNamespace,n===null?e.removeAttribute(t):(o=o.type,n=o===3||o===4&&n===!0?"":""+n,r?e.setAttributeNS(r,t,n):e.setAttribute(t,n))))}var Ir=Sk.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,Es=Symbol.for("react.element"),ha=Symbol.for("react.portal"),ba=Symbol.for("react.fragment"),dp=Symbol.for("react.strict_mode"),hf=Symbol.for("react.profiler"),Rb=Symbol.for("react.provider"),Eb=Symbol.for("react.context"),fp=Symbol.for("react.forward_ref"),bf=Symbol.for("react.suspense"),xf=Symbol.for("react.suspense_list"),pp=Symbol.for("react.memo"),Vr=Symbol.for("react.lazy");Symbol.for("react.scope");Symbol.for("react.debug_trace_mode");var Pb=Symbol.for("react.offscreen");Symbol.for("react.legacy_hidden");Symbol.for("react.cache");Symbol.for("react.tracing_marker");var Ih=Symbol.iterator;function Nl(e){return e===null||typeof e!="object"?null:(e=Ih&&e[Ih]||e["@@iterator"],typeof e=="function"?e:null)}var qe=Object.assign,Gd;function jl(e){if(Gd===void 0)try{throw Error()}catch(n){var t=n.stack.trim().match(/\n( *(at )?)/);Gd=t&&t[1]||""}return`
`+Gd+e}var qd=!1;function Yd(e,t){if(!e||qd)return"";qd=!0;var n=Error.prepareStackTrace;Error.prepareStackTrace=void 0;try{if(t)if(t=function(){throw Error()},Object.defineProperty(t.prototype,"props",{set:function(){throw Error()}}),typeof Reflect=="object"&&Reflect.construct){try{Reflect.construct(t,[])}catch(c){var r=c}Reflect.construct(e,[],t)}else{try{t.call()}catch(c){r=c}e.call(t.prototype)}else{try{throw Error()}catch(c){r=c}e()}}catch(c){if(c&&r&&typeof c.stack=="string"){for(var o=c.stack.split(`
`),a=r.stack.split(`
`),l=o.length-1,i=a.length-1;1<=l&&0<=i&&o[l]!==a[i];)i--;for(;1<=l&&0<=i;l--,i--)if(o[l]!==a[i]){if(l!==1||i!==1)do if(l--,i--,0>i||o[l]!==a[i]){var s=`
`+o[l].replace(" at new "," at ");return e.displayName&&s.includes("<anonymous>")&&(s=s.replace("<anonymous>",e.displayName)),s}while(1<=l&&0<=i);break}}}finally{qd=!1,Error.prepareStackTrace=n}return(e=e?e.displayName||e.name:"")?jl(e):""}function Pk(e){switch(e.tag){case 5:return jl(e.type);case 16:return jl("Lazy");case 13:return jl("Suspense");case 19:return jl("SuspenseList");case 0:case 2:case 15:return e=Yd(e.type,!1),e;case 11:return e=Yd(e.type.render,!1),e;case 1:return e=Yd(e.type,!0),e;default:return""}}function yf(e){if(e==null)return null;if(typeof e=="function")return e.displayName||e.name||null;if(typeof e=="string")return e;switch(e){case ba:return"Fragment";case ha:return"Portal";case hf:return"Profiler";case dp:return"StrictMode";case bf:return"Suspense";case xf:return"SuspenseList"}if(typeof e=="object")switch(e.$$typeof){case Eb:return(e.displayName||"Context")+".Consumer";case Rb:return(e._context.displayName||"Context")+".Provider";case fp:var t=e.render;return e=e.displayName,e||(e=t.displayName||t.name||"",e=e!==""?"ForwardRef("+e+")":"ForwardRef"),e;case pp:return t=e.displayName||null,t!==null?t:yf(e.type)||"Memo";case Vr:t=e._payload,e=e._init;try{return yf(e(t))}catch{}}return null}function _k(e){var t=e.type;switch(e.tag){case 24:return"Cache";case 9:return(t.displayName||"Context")+".Consumer";case 10:return(t._context.displayName||"Context")+".Provider";case 18:return"DehydratedFragment";case 11:return e=t.render,e=e.displayName||e.name||"",t.displayName||(e!==""?"ForwardRef("+e+")":"ForwardRef");case 7:return"Fragment";case 5:return t;case 4:return"Portal";case 3:return"Root";case 6:return"Text";case 16:return yf(t);case 8:return t===dp?"StrictMode":"Mode";case 22:return"Offscreen";case 12:return"Profiler";case 21:return"Scope";case 13:return"Suspense";case 19:return"SuspenseList";case 25:return"TracingMarker";case 1:case 0:case 17:case 2:case 14:case 15:if(typeof t=="function")return t.displayName||t.name||null;if(typeof t=="string")return t}return null}function no(e){switch(typeof e){case"boolean":case"number":case"string":case"undefined":return e;case"object":return e;default:return""}}function _b(e){var t=e.type;return(e=e.nodeName)&&e.toLowerCase()==="input"&&(t==="checkbox"||t==="radio")}function Lk(e){var t=_b(e)?"checked":"value",n=Object.getOwnPropertyDescriptor(e.constructor.prototype,t),r=""+e[t];if(!e.hasOwnProperty(t)&&typeof n<"u"&&typeof n.get=="function"&&typeof n.set=="function"){var o=n.get,a=n.set;return Object.defineProperty(e,t,{configurable:!0,get:function(){return o.call(this)},set:function(l){r=""+l,a.call(this,l)}}),Object.defineProperty(e,t,{enumerable:n.enumerable}),{getValue:function(){return r},setValue:function(l){r=""+l},stopTracking:function(){e._valueTracker=null,delete e[t]}}}}function Ps(e){e._valueTracker||(e._valueTracker=Lk(e))}function Lb(e){if(!e)return!1;var t=e._valueTracker;if(!t)return!0;var n=t.getValue(),r="";return e&&(r=_b(e)?e.checked?"true":"false":e.value),e=r,e!==n?(t.setValue(e),!0):!1}function rc(e){if(e=e||(typeof document<"u"?document:void 0),typeof e>"u")return null;try{return e.activeElement||e.body}catch{return e.body}}function wf(e,t){var n=t.checked;return qe({},t,{defaultChecked:void 0,defaultValue:void 0,value:void 0,checked:n??e._wrapperState.initialChecked})}function Ch(e,t){var n=t.defaultValue==null?"":t.defaultValue,r=t.checked!=null?t.checked:t.defaultChecked;n=no(t.value!=null?t.value:n),e._wrapperState={initialChecked:r,initialValue:n,controlled:t.type==="checkbox"||t.type==="radio"?t.checked!=null:t.value!=null}}function Ob(e,t){t=t.checked,t!=null&&up(e,"checked",t,!1)}function If(e,t){Ob(e,t);var n=no(t.value),r=t.type;if(n!=null)r==="number"?(n===0&&e.value===""||e.value!=n)&&(e.value=""+n):e.value!==""+n&&(e.value=""+n);else if(r==="submit"||r==="reset"){e.removeAttribute("value");return}t.hasOwnProperty("value")?Cf(e,t.type,n):t.hasOwnProperty("defaultValue")&&Cf(e,t.type,no(t.defaultValue)),t.checked==null&&t.defaultChecked!=null&&(e.defaultChecked=!!t.defaultChecked)}function Sh(e,t,n){if(t.hasOwnProperty("value")||t.hasOwnProperty("defaultValue")){var r=t.type;if(!(r!=="submit"&&r!=="reset"||t.value!==void 0&&t.value!==null))return;t=""+e._wrapperState.initialValue,n||t===e.value||(e.value=t),e.defaultValue=t}n=e.name,n!==""&&(e.name=""),e.defaultChecked=!!e._wrapperState.initialChecked,n!==""&&(e.name=n)}function Cf(e,t,n){(t!=="number"||rc(e.ownerDocument)!==e)&&(n==null?e.defaultValue=""+e._wrapperState.initialValue:e.defaultValue!==""+n&&(e.defaultValue=""+n))}var Vl=Array.isArray;function Pa(e,t,n,r){if(e=e.options,t){t={};for(var o=0;o<n.length;o++)t["$"+n[o]]=!0;for(n=0;n<e.length;n++)o=t.hasOwnProperty("$"+e[n].value),e[n].selected!==o&&(e[n].selected=o),o&&r&&(e[n].defaultSelected=!0)}else{for(n=""+no(n),t=null,o=0;o<e.length;o++){if(e[o].value===n){e[o].selected=!0,r&&(e[o].defaultSelected=!0);return}t!==null||e[o].disabled||(t=e[o])}t!==null&&(t.selected=!0)}}function Sf(e,t){if(t.dangerouslySetInnerHTML!=null)throw Error(H(91));return qe({},t,{value:void 0,defaultValue:void 0,children:""+e._wrapperState.initialValue})}function kh(e,t){var n=t.value;if(n==null){if(n=t.children,t=t.defaultValue,n!=null){if(t!=null)throw Error(H(92));if(Vl(n)){if(1<n.length)throw Error(H(93));n=n[0]}t=n}t==null&&(t=""),n=t}e._wrapperState={initialValue:no(n)}}function Nb(e,t){var n=no(t.value),r=no(t.defaultValue);n!=null&&(n=""+n,n!==e.value&&(e.value=n),t.defaultValue==null&&e.defaultValue!==n&&(e.defaultValue=n)),r!=null&&(e.defaultValue=""+r)}function Th(e){var t=e.textContent;t===e._wrapperState.initialValue&&t!==""&&t!==null&&(e.value=t)}function Bb(e){switch(e){case"svg":return"http://www.w3.org/2000/svg";case"math":return"http://www.w3.org/1998/Math/MathML";default:return"http://www.w3.org/1999/xhtml"}}function kf(e,t){return e==null||e==="http://www.w3.org/1999/xhtml"?Bb(t):e==="http://www.w3.org/2000/svg"&&t==="foreignObject"?"http://www.w3.org/1999/xhtml":e}var _s,Ab=(function(e){return typeof MSApp<"u"&&MSApp.execUnsafeLocalFunction?function(t,n,r,o){MSApp.execUnsafeLocalFunction(function(){return e(t,n,r,o)})}:e})(function(e,t){if(e.namespaceURI!=="http://www.w3.org/2000/svg"||"innerHTML"in e)e.innerHTML=t;else{for(_s=_s||document.createElement("div"),_s.innerHTML="<svg>"+t.valueOf().toString()+"</svg>",t=_s.firstChild;e.firstChild;)e.removeChild(e.firstChild);for(;t.firstChild;)e.appendChild(t.firstChild)}});function ti(e,t){if(t){var n=e.firstChild;if(n&&n===e.lastChild&&n.nodeType===3){n.nodeValue=t;return}}e.textContent=t}var Ul={animationIterationCount:!0,aspectRatio:!0,borderImageOutset:!0,borderImageSlice:!0,borderImageWidth:!0,boxFlex:!0,boxFlexGroup:!0,boxOrdinalGroup:!0,columnCount:!0,columns:!0,flex:!0,flexGrow:!0,flexPositive:!0,flexShrink:!0,flexNegative:!0,flexOrder:!0,gridArea:!0,gridRow:!0,gridRowEnd:!0,gridRowSpan:!0,gridRowStart:!0,gridColumn:!0,gridColumnEnd:!0,gridColumnSpan:!0,gridColumnStart:!0,fontWeight:!0,lineClamp:!0,lineHeight:!0,opacity:!0,order:!0,orphans:!0,tabSize:!0,widows:!0,zIndex:!0,zoom:!0,fillOpacity:!0,floodOpacity:!0,stopOpacity:!0,strokeDasharray:!0,strokeDashoffset:!0,strokeMiterlimit:!0,strokeOpacity:!0,strokeWidth:!0},Ok=["Webkit","ms","Moz","O"];Object.keys(Ul).forEach(function(e){Ok.forEach(function(t){t=t+e.charAt(0).toUpperCase()+e.substring(1),Ul[t]=Ul[e]})});function Fb(e,t,n){return t==null||typeof t=="boolean"||t===""?"":n||typeof t!="number"||t===0||Ul.hasOwnProperty(e)&&Ul[e]?(""+t).trim():t+"px"}function Mb(e,t){e=e.style;for(var n in t)if(t.hasOwnProperty(n)){var r=n.indexOf("--")===0,o=Fb(n,t[n],r);n==="float"&&(n="cssFloat"),r?e.setProperty(n,o):e[n]=o}}var Nk=qe({menuitem:!0},{area:!0,base:!0,br:!0,col:!0,embed:!0,hr:!0,img:!0,input:!0,keygen:!0,link:!0,meta:!0,param:!0,source:!0,track:!0,wbr:!0});function Tf(e,t){if(t){if(Nk[e]&&(t.children!=null||t.dangerouslySetInnerHTML!=null))throw Error(H(137,e));if(t.dangerouslySetInnerHTML!=null){if(t.children!=null)throw Error(H(60));if(typeof t.dangerouslySetInnerHTML!="object"||!("__html"in t.dangerouslySetInnerHTML))throw Error(H(61))}if(t.style!=null&&typeof t.style!="object")throw Error(H(62))}}function Rf(e,t){if(e.indexOf("-")===-1)return typeof t.is=="string";switch(e){case"annotation-xml":case"color-profile":case"font-face":case"font-face-src":case"font-face-uri":case"font-face-format":case"font-face-name":case"missing-glyph":return!1;default:return!0}}var Ef=null;function mp(e){return e=e.target||e.srcElement||window,e.correspondingUseElement&&(e=e.correspondingUseElement),e.nodeType===3?e.parentNode:e}var Pf=null,_a=null,La=null;function Rh(e){if(e=xi(e)){if(typeof Pf!="function")throw Error(H(280));var t=e.stateNode;t&&(t=Lc(t),Pf(e.stateNode,e.type,t))}}function Db(e){_a?La?La.push(e):La=[e]:_a=e}function zb(){if(_a){var e=_a,t=La;if(La=_a=null,Rh(e),t)for(e=0;e<t.length;e++)Rh(t[e])}}function Wb(e,t){return e(t)}function jb(){}var Qd=!1;function Vb(e,t,n){if(Qd)return e(t,n);Qd=!0;try{return Wb(e,t,n)}finally{Qd=!1,(_a!==null||La!==null)&&(jb(),zb())}}function ni(e,t){var n=e.stateNode;if(n===null)return null;var r=Lc(n);if(r===null)return null;n=r[t];e:switch(t){case"onClick":case"onClickCapture":case"onDoubleClick":case"onDoubleClickCapture":case"onMouseDown":case"onMouseDownCapture":case"onMouseMove":case"onMouseMoveCapture":case"onMouseUp":case"onMouseUpCapture":case"onMouseEnter":(r=!r.disabled)||(e=e.type,r=!(e==="button"||e==="input"||e==="select"||e==="textarea")),e=!r;break e;default:e=!1}if(e)return null;if(n&&typeof n!="function")throw Error(H(231,t,typeof n));return n}var _f=!1;if(br)try{va={},Object.defineProperty(va,"passive",{get:function(){_f=!0}}),window.addEventListener("test",va,va),window.removeEventListener("test",va,va)}catch{_f=!1}var va;function Bk(e,t,n,r,o,a,l,i,s){var c=Array.prototype.slice.call(arguments,3);try{t.apply(n,c)}catch(d){this.onError(d)}}var Kl=!1,oc=null,ac=!1,Lf=null,Ak={onError:function(e){Kl=!0,oc=e}};function Fk(e,t,n,r,o,a,l,i,s){Kl=!1,oc=null,Bk.apply(Ak,arguments)}function Mk(e,t,n,r,o,a,l,i,s){if(Fk.apply(this,arguments),Kl){if(Kl){var c=oc;Kl=!1,oc=null}else throw Error(H(198));ac||(ac=!0,Lf=c)}}function Go(e){var t=e,n=e;if(e.alternate)for(;t.return;)t=t.return;else{e=t;do t=e,(t.flags&4098)!==0&&(n=t.return),e=t.return;while(e)}return t.tag===3?n:null}function Hb(e){if(e.tag===13){var t=e.memoizedState;if(t===null&&(e=e.alternate,e!==null&&(t=e.memoizedState)),t!==null)return t.dehydrated}return null}function Eh(e){if(Go(e)!==e)throw Error(H(188))}function Dk(e){var t=e.alternate;if(!t){if(t=Go(e),t===null)throw Error(H(188));return t!==e?null:e}for(var n=e,r=t;;){var o=n.return;if(o===null)break;var a=o.alternate;if(a===null){if(r=o.return,r!==null){n=r;continue}break}if(o.child===a.child){for(a=o.child;a;){if(a===n)return Eh(o),e;if(a===r)return Eh(o),t;a=a.sibling}throw Error(H(188))}if(n.return!==r.return)n=o,r=a;else{for(var l=!1,i=o.child;i;){if(i===n){l=!0,n=o,r=a;break}if(i===r){l=!0,r=o,n=a;break}i=i.sibling}if(!l){for(i=a.child;i;){if(i===n){l=!0,n=a,r=o;break}if(i===r){l=!0,r=a,n=o;break}i=i.sibling}if(!l)throw Error(H(189))}}if(n.alternate!==r)throw Error(H(190))}if(n.tag!==3)throw Error(H(188));return n.stateNode.current===n?e:t}function $b(e){return e=Dk(e),e!==null?Ub(e):null}function Ub(e){if(e.tag===5||e.tag===6)return e;for(e=e.child;e!==null;){var t=Ub(e);if(t!==null)return t;e=e.sibling}return null}var Kb=Gt.unstable_scheduleCallback,Ph=Gt.unstable_cancelCallback,zk=Gt.unstable_shouldYield,Wk=Gt.unstable_requestPaint,Xe=Gt.unstable_now,jk=Gt.unstable_getCurrentPriorityLevel,vp=Gt.unstable_ImmediatePriority,Gb=Gt.unstable_UserBlockingPriority,lc=Gt.unstable_NormalPriority,Vk=Gt.unstable_LowPriority,qb=Gt.unstable_IdlePriority,Rc=null,Yn=null;function Hk(e){if(Yn&&typeof Yn.onCommitFiberRoot=="function")try{Yn.onCommitFiberRoot(Rc,e,void 0,(e.current.flags&128)===128)}catch{}}var Rn=Math.clz32?Math.clz32:Kk,$k=Math.log,Uk=Math.LN2;function Kk(e){return e>>>=0,e===0?32:31-($k(e)/Uk|0)|0}var Ls=64,Os=4194304;function Hl(e){switch(e&-e){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;case 16:return 16;case 32:return 32;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return e&4194240;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return e&130023424;case 134217728:return 134217728;case 268435456:return 268435456;case 536870912:return 536870912;case 1073741824:return 1073741824;default:return e}}function ic(e,t){var n=e.pendingLanes;if(n===0)return 0;var r=0,o=e.suspendedLanes,a=e.pingedLanes,l=n&268435455;if(l!==0){var i=l&~o;i!==0?r=Hl(i):(a&=l,a!==0&&(r=Hl(a)))}else l=n&~o,l!==0?r=Hl(l):a!==0&&(r=Hl(a));if(r===0)return 0;if(t!==0&&t!==r&&(t&o)===0&&(o=r&-r,a=t&-t,o>=a||o===16&&(a&4194240)!==0))return t;if((r&4)!==0&&(r|=n&16),t=e.entangledLanes,t!==0)for(e=e.entanglements,t&=r;0<t;)n=31-Rn(t),o=1<<n,r|=e[n],t&=~o;return r}function Gk(e,t){switch(e){case 1:case 2:case 4:return t+250;case 8:case 16:case 32:case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return t+5e3;case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:return-1;case 134217728:case 268435456:case 536870912:case 1073741824:return-1;default:return-1}}function qk(e,t){for(var n=e.suspendedLanes,r=e.pingedLanes,o=e.expirationTimes,a=e.pendingLanes;0<a;){var l=31-Rn(a),i=1<<l,s=o[l];s===-1?((i&n)===0||(i&r)!==0)&&(o[l]=Gk(i,t)):s<=t&&(e.expiredLanes|=i),a&=~i}}function Of(e){return e=e.pendingLanes&-1073741825,e!==0?e:e&1073741824?1073741824:0}function Yb(){var e=Ls;return Ls<<=1,(Ls&4194240)===0&&(Ls=64),e}function Xd(e){for(var t=[],n=0;31>n;n++)t.push(e);return t}function hi(e,t,n){e.pendingLanes|=t,t!==536870912&&(e.suspendedLanes=0,e.pingedLanes=0),e=e.eventTimes,t=31-Rn(t),e[t]=n}function Yk(e,t){var n=e.pendingLanes&~t;e.pendingLanes=t,e.suspendedLanes=0,e.pingedLanes=0,e.expiredLanes&=t,e.mutableReadLanes&=t,e.entangledLanes&=t,t=e.entanglements;var r=e.eventTimes;for(e=e.expirationTimes;0<n;){var o=31-Rn(n),a=1<<o;t[o]=0,r[o]=-1,e[o]=-1,n&=~a}}function gp(e,t){var n=e.entangledLanes|=t;for(e=e.entanglements;n;){var r=31-Rn(n),o=1<<r;o&t|e[r]&t&&(e[r]|=t),n&=~o}}var Pe=0;function Qb(e){return e&=-e,1<e?4<e?(e&268435455)!==0?16:536870912:4:1}var Xb,hp,Zb,Jb,ex,Nf=!1,Ns=[],qr=null,Yr=null,Qr=null,ri=new Map,oi=new Map,$r=[],Qk="mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");function _h(e,t){switch(e){case"focusin":case"focusout":qr=null;break;case"dragenter":case"dragleave":Yr=null;break;case"mouseover":case"mouseout":Qr=null;break;case"pointerover":case"pointerout":ri.delete(t.pointerId);break;case"gotpointercapture":case"lostpointercapture":oi.delete(t.pointerId)}}function Bl(e,t,n,r,o,a){return e===null||e.nativeEvent!==a?(e={blockedOn:t,domEventName:n,eventSystemFlags:r,nativeEvent:a,targetContainers:[o]},t!==null&&(t=xi(t),t!==null&&hp(t)),e):(e.eventSystemFlags|=r,t=e.targetContainers,o!==null&&t.indexOf(o)===-1&&t.push(o),e)}function Xk(e,t,n,r,o){switch(t){case"focusin":return qr=Bl(qr,e,t,n,r,o),!0;case"dragenter":return Yr=Bl(Yr,e,t,n,r,o),!0;case"mouseover":return Qr=Bl(Qr,e,t,n,r,o),!0;case"pointerover":var a=o.pointerId;return ri.set(a,Bl(ri.get(a)||null,e,t,n,r,o)),!0;case"gotpointercapture":return a=o.pointerId,oi.set(a,Bl(oi.get(a)||null,e,t,n,r,o)),!0}return!1}function tx(e){var t=Fo(e.target);if(t!==null){var n=Go(t);if(n!==null){if(t=n.tag,t===13){if(t=Hb(n),t!==null){e.blockedOn=t,ex(e.priority,function(){Zb(n)});return}}else if(t===3&&n.stateNode.current.memoizedState.isDehydrated){e.blockedOn=n.tag===3?n.stateNode.containerInfo:null;return}}}e.blockedOn=null}function Gs(e){if(e.blockedOn!==null)return!1;for(var t=e.targetContainers;0<t.length;){var n=Bf(e.domEventName,e.eventSystemFlags,t[0],e.nativeEvent);if(n===null){n=e.nativeEvent;var r=new n.constructor(n.type,n);Ef=r,n.target.dispatchEvent(r),Ef=null}else return t=xi(n),t!==null&&hp(t),e.blockedOn=n,!1;t.shift()}return!0}function Lh(e,t,n){Gs(e)&&n.delete(t)}function Zk(){Nf=!1,qr!==null&&Gs(qr)&&(qr=null),Yr!==null&&Gs(Yr)&&(Yr=null),Qr!==null&&Gs(Qr)&&(Qr=null),ri.forEach(Lh),oi.forEach(Lh)}function Al(e,t){e.blockedOn===t&&(e.blockedOn=null,Nf||(Nf=!0,Gt.unstable_scheduleCallback(Gt.unstable_NormalPriority,Zk)))}function ai(e){function t(o){return Al(o,e)}if(0<Ns.length){Al(Ns[0],e);for(var n=1;n<Ns.length;n++){var r=Ns[n];r.blockedOn===e&&(r.blockedOn=null)}}for(qr!==null&&Al(qr,e),Yr!==null&&Al(Yr,e),Qr!==null&&Al(Qr,e),ri.forEach(t),oi.forEach(t),n=0;n<$r.length;n++)r=$r[n],r.blockedOn===e&&(r.blockedOn=null);for(;0<$r.length&&(n=$r[0],n.blockedOn===null);)tx(n),n.blockedOn===null&&$r.shift()}var Oa=Ir.ReactCurrentBatchConfig,sc=!0;function Jk(e,t,n,r){var o=Pe,a=Oa.transition;Oa.transition=null;try{Pe=1,bp(e,t,n,r)}finally{Pe=o,Oa.transition=a}}function eT(e,t,n,r){var o=Pe,a=Oa.transition;Oa.transition=null;try{Pe=4,bp(e,t,n,r)}finally{Pe=o,Oa.transition=a}}function bp(e,t,n,r){if(sc){var o=Bf(e,t,n,r);if(o===null)of(e,t,r,cc,n),_h(e,r);else if(Xk(o,e,t,n,r))r.stopPropagation();else if(_h(e,r),t&4&&-1<Qk.indexOf(e)){for(;o!==null;){var a=xi(o);if(a!==null&&Xb(a),a=Bf(e,t,n,r),a===null&&of(e,t,r,cc,n),a===o)break;o=a}o!==null&&r.stopPropagation()}else of(e,t,r,null,n)}}var cc=null;function Bf(e,t,n,r){if(cc=null,e=mp(r),e=Fo(e),e!==null)if(t=Go(e),t===null)e=null;else if(n=t.tag,n===13){if(e=Hb(t),e!==null)return e;e=null}else if(n===3){if(t.stateNode.current.memoizedState.isDehydrated)return t.tag===3?t.stateNode.containerInfo:null;e=null}else t!==e&&(e=null);return cc=e,null}function nx(e){switch(e){case"cancel":case"click":case"close":case"contextmenu":case"copy":case"cut":case"auxclick":case"dblclick":case"dragend":case"dragstart":case"drop":case"focusin":case"focusout":case"input":case"invalid":case"keydown":case"keypress":case"keyup":case"mousedown":case"mouseup":case"paste":case"pause":case"play":case"pointercancel":case"pointerdown":case"pointerup":case"ratechange":case"reset":case"resize":case"seeked":case"submit":case"touchcancel":case"touchend":case"touchstart":case"volumechange":case"change":case"selectionchange":case"textInput":case"compositionstart":case"compositionend":case"compositionupdate":case"beforeblur":case"afterblur":case"beforeinput":case"blur":case"fullscreenchange":case"focus":case"hashchange":case"popstate":case"select":case"selectstart":return 1;case"drag":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"mousemove":case"mouseout":case"mouseover":case"pointermove":case"pointerout":case"pointerover":case"scroll":case"toggle":case"touchmove":case"wheel":case"mouseenter":case"mouseleave":case"pointerenter":case"pointerleave":return 4;case"message":switch(jk()){case vp:return 1;case Gb:return 4;case lc:case Vk:return 16;case qb:return 536870912;default:return 16}default:return 16}}var Kr=null,xp=null,qs=null;function rx(){if(qs)return qs;var e,t=xp,n=t.length,r,o="value"in Kr?Kr.value:Kr.textContent,a=o.length;for(e=0;e<n&&t[e]===o[e];e++);var l=n-e;for(r=1;r<=l&&t[n-r]===o[a-r];r++);return qs=o.slice(e,1<r?1-r:void 0)}function Ys(e){var t=e.keyCode;return"charCode"in e?(e=e.charCode,e===0&&t===13&&(e=13)):e=t,e===10&&(e=13),32<=e||e===13?e:0}function Bs(){return!0}function Oh(){return!1}function qt(e){function t(n,r,o,a,l){this._reactName=n,this._targetInst=o,this.type=r,this.nativeEvent=a,this.target=l,this.currentTarget=null;for(var i in e)e.hasOwnProperty(i)&&(n=e[i],this[i]=n?n(a):a[i]);return this.isDefaultPrevented=(a.defaultPrevented!=null?a.defaultPrevented:a.returnValue===!1)?Bs:Oh,this.isPropagationStopped=Oh,this}return qe(t.prototype,{preventDefault:function(){this.defaultPrevented=!0;var n=this.nativeEvent;n&&(n.preventDefault?n.preventDefault():typeof n.returnValue!="unknown"&&(n.returnValue=!1),this.isDefaultPrevented=Bs)},stopPropagation:function(){var n=this.nativeEvent;n&&(n.stopPropagation?n.stopPropagation():typeof n.cancelBubble!="unknown"&&(n.cancelBubble=!0),this.isPropagationStopped=Bs)},persist:function(){},isPersistent:Bs}),t}var Va={eventPhase:0,bubbles:0,cancelable:0,timeStamp:function(e){return e.timeStamp||Date.now()},defaultPrevented:0,isTrusted:0},yp=qt(Va),bi=qe({},Va,{view:0,detail:0}),tT=qt(bi),Zd,Jd,Fl,Ec=qe({},bi,{screenX:0,screenY:0,clientX:0,clientY:0,pageX:0,pageY:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,getModifierState:wp,button:0,buttons:0,relatedTarget:function(e){return e.relatedTarget===void 0?e.fromElement===e.srcElement?e.toElement:e.fromElement:e.relatedTarget},movementX:function(e){return"movementX"in e?e.movementX:(e!==Fl&&(Fl&&e.type==="mousemove"?(Zd=e.screenX-Fl.screenX,Jd=e.screenY-Fl.screenY):Jd=Zd=0,Fl=e),Zd)},movementY:function(e){return"movementY"in e?e.movementY:Jd}}),Nh=qt(Ec),nT=qe({},Ec,{dataTransfer:0}),rT=qt(nT),oT=qe({},bi,{relatedTarget:0}),ef=qt(oT),aT=qe({},Va,{animationName:0,elapsedTime:0,pseudoElement:0}),lT=qt(aT),iT=qe({},Va,{clipboardData:function(e){return"clipboardData"in e?e.clipboardData:window.clipboardData}}),sT=qt(iT),cT=qe({},Va,{data:0}),Bh=qt(cT),uT={Esc:"Escape",Spacebar:" ",Left:"ArrowLeft",Up:"ArrowUp",Right:"ArrowRight",Down:"ArrowDown",Del:"Delete",Win:"OS",Menu:"ContextMenu",Apps:"ContextMenu",Scroll:"ScrollLock",MozPrintableKey:"Unidentified"},dT={8:"Backspace",9:"Tab",12:"Clear",13:"Enter",16:"Shift",17:"Control",18:"Alt",19:"Pause",20:"CapsLock",27:"Escape",32:" ",33:"PageUp",34:"PageDown",35:"End",36:"Home",37:"ArrowLeft",38:"ArrowUp",39:"ArrowRight",40:"ArrowDown",45:"Insert",46:"Delete",112:"F1",113:"F2",114:"F3",115:"F4",116:"F5",117:"F6",118:"F7",119:"F8",120:"F9",121:"F10",122:"F11",123:"F12",144:"NumLock",145:"ScrollLock",224:"Meta"},fT={Alt:"altKey",Control:"ctrlKey",Meta:"metaKey",Shift:"shiftKey"};function pT(e){var t=this.nativeEvent;return t.getModifierState?t.getModifierState(e):(e=fT[e])?!!t[e]:!1}function wp(){return pT}var mT=qe({},bi,{key:function(e){if(e.key){var t=uT[e.key]||e.key;if(t!=="Unidentified")return t}return e.type==="keypress"?(e=Ys(e),e===13?"Enter":String.fromCharCode(e)):e.type==="keydown"||e.type==="keyup"?dT[e.keyCode]||"Unidentified":""},code:0,location:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,repeat:0,locale:0,getModifierState:wp,charCode:function(e){return e.type==="keypress"?Ys(e):0},keyCode:function(e){return e.type==="keydown"||e.type==="keyup"?e.keyCode:0},which:function(e){return e.type==="keypress"?Ys(e):e.type==="keydown"||e.type==="keyup"?e.keyCode:0}}),vT=qt(mT),gT=qe({},Ec,{pointerId:0,width:0,height:0,pressure:0,tangentialPressure:0,tiltX:0,tiltY:0,twist:0,pointerType:0,isPrimary:0}),Ah=qt(gT),hT=qe({},bi,{touches:0,targetTouches:0,changedTouches:0,altKey:0,metaKey:0,ctrlKey:0,shiftKey:0,getModifierState:wp}),bT=qt(hT),xT=qe({},Va,{propertyName:0,elapsedTime:0,pseudoElement:0}),yT=qt(xT),wT=qe({},Ec,{deltaX:function(e){return"deltaX"in e?e.deltaX:"wheelDeltaX"in e?-e.wheelDeltaX:0},deltaY:function(e){return"deltaY"in e?e.deltaY:"wheelDeltaY"in e?-e.wheelDeltaY:"wheelDelta"in e?-e.wheelDelta:0},deltaZ:0,deltaMode:0}),IT=qt(wT),CT=[9,13,27,32],Ip=br&&"CompositionEvent"in window,Gl=null;br&&"documentMode"in document&&(Gl=document.documentMode);var ST=br&&"TextEvent"in window&&!Gl,ox=br&&(!Ip||Gl&&8<Gl&&11>=Gl),Fh=" ",Mh=!1;function ax(e,t){switch(e){case"keyup":return CT.indexOf(t.keyCode)!==-1;case"keydown":return t.keyCode!==229;case"keypress":case"mousedown":case"focusout":return!0;default:return!1}}function lx(e){return e=e.detail,typeof e=="object"&&"data"in e?e.data:null}var xa=!1;function kT(e,t){switch(e){case"compositionend":return lx(t);case"keypress":return t.which!==32?null:(Mh=!0,Fh);case"textInput":return e=t.data,e===Fh&&Mh?null:e;default:return null}}function TT(e,t){if(xa)return e==="compositionend"||!Ip&&ax(e,t)?(e=rx(),qs=xp=Kr=null,xa=!1,e):null;switch(e){case"paste":return null;case"keypress":if(!(t.ctrlKey||t.altKey||t.metaKey)||t.ctrlKey&&t.altKey){if(t.char&&1<t.char.length)return t.char;if(t.which)return String.fromCharCode(t.which)}return null;case"compositionend":return ox&&t.locale!=="ko"?null:t.data;default:return null}}var RT={color:!0,date:!0,datetime:!0,"datetime-local":!0,email:!0,month:!0,number:!0,password:!0,range:!0,search:!0,tel:!0,text:!0,time:!0,url:!0,week:!0};function Dh(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t==="input"?!!RT[e.type]:t==="textarea"}function ix(e,t,n,r){Db(r),t=uc(t,"onChange"),0<t.length&&(n=new yp("onChange","change",null,n,r),e.push({event:n,listeners:t}))}var ql=null,li=null;function ET(e){bx(e,0)}function Pc(e){var t=Ia(e);if(Lb(t))return e}function PT(e,t){if(e==="change")return t}var sx=!1;br&&(br?(Fs="oninput"in document,Fs||(tf=document.createElement("div"),tf.setAttribute("oninput","return;"),Fs=typeof tf.oninput=="function"),As=Fs):As=!1,sx=As&&(!document.documentMode||9<document.documentMode));var As,Fs,tf;function zh(){ql&&(ql.detachEvent("onpropertychange",cx),li=ql=null)}function cx(e){if(e.propertyName==="value"&&Pc(li)){var t=[];ix(t,li,e,mp(e)),Vb(ET,t)}}function _T(e,t,n){e==="focusin"?(zh(),ql=t,li=n,ql.attachEvent("onpropertychange",cx)):e==="focusout"&&zh()}function LT(e){if(e==="selectionchange"||e==="keyup"||e==="keydown")return Pc(li)}function OT(e,t){if(e==="click")return Pc(t)}function NT(e,t){if(e==="input"||e==="change")return Pc(t)}function BT(e,t){return e===t&&(e!==0||1/e===1/t)||e!==e&&t!==t}var Pn=typeof Object.is=="function"?Object.is:BT;function ii(e,t){if(Pn(e,t))return!0;if(typeof e!="object"||e===null||typeof t!="object"||t===null)return!1;var n=Object.keys(e),r=Object.keys(t);if(n.length!==r.length)return!1;for(r=0;r<n.length;r++){var o=n[r];if(!gf.call(t,o)||!Pn(e[o],t[o]))return!1}return!0}function Wh(e){for(;e&&e.firstChild;)e=e.firstChild;return e}function jh(e,t){var n=Wh(e);e=0;for(var r;n;){if(n.nodeType===3){if(r=e+n.textContent.length,e<=t&&r>=t)return{node:n,offset:t-e};e=r}e:{for(;n;){if(n.nextSibling){n=n.nextSibling;break e}n=n.parentNode}n=void 0}n=Wh(n)}}function ux(e,t){return e&&t?e===t?!0:e&&e.nodeType===3?!1:t&&t.nodeType===3?ux(e,t.parentNode):"contains"in e?e.contains(t):e.compareDocumentPosition?!!(e.compareDocumentPosition(t)&16):!1:!1}function dx(){for(var e=window,t=rc();t instanceof e.HTMLIFrameElement;){try{var n=typeof t.contentWindow.location.href=="string"}catch{n=!1}if(n)e=t.contentWindow;else break;t=rc(e.document)}return t}function Cp(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t&&(t==="input"&&(e.type==="text"||e.type==="search"||e.type==="tel"||e.type==="url"||e.type==="password")||t==="textarea"||e.contentEditable==="true")}function AT(e){var t=dx(),n=e.focusedElem,r=e.selectionRange;if(t!==n&&n&&n.ownerDocument&&ux(n.ownerDocument.documentElement,n)){if(r!==null&&Cp(n)){if(t=r.start,e=r.end,e===void 0&&(e=t),"selectionStart"in n)n.selectionStart=t,n.selectionEnd=Math.min(e,n.value.length);else if(e=(t=n.ownerDocument||document)&&t.defaultView||window,e.getSelection){e=e.getSelection();var o=n.textContent.length,a=Math.min(r.start,o);r=r.end===void 0?a:Math.min(r.end,o),!e.extend&&a>r&&(o=r,r=a,a=o),o=jh(n,a);var l=jh(n,r);o&&l&&(e.rangeCount!==1||e.anchorNode!==o.node||e.anchorOffset!==o.offset||e.focusNode!==l.node||e.focusOffset!==l.offset)&&(t=t.createRange(),t.setStart(o.node,o.offset),e.removeAllRanges(),a>r?(e.addRange(t),e.extend(l.node,l.offset)):(t.setEnd(l.node,l.offset),e.addRange(t)))}}for(t=[],e=n;e=e.parentNode;)e.nodeType===1&&t.push({element:e,left:e.scrollLeft,top:e.scrollTop});for(typeof n.focus=="function"&&n.focus(),n=0;n<t.length;n++)e=t[n],e.element.scrollLeft=e.left,e.element.scrollTop=e.top}}var FT=br&&"documentMode"in document&&11>=document.documentMode,ya=null,Af=null,Yl=null,Ff=!1;function Vh(e,t,n){var r=n.window===n?n.document:n.nodeType===9?n:n.ownerDocument;Ff||ya==null||ya!==rc(r)||(r=ya,"selectionStart"in r&&Cp(r)?r={start:r.selectionStart,end:r.selectionEnd}:(r=(r.ownerDocument&&r.ownerDocument.defaultView||window).getSelection(),r={anchorNode:r.anchorNode,anchorOffset:r.anchorOffset,focusNode:r.focusNode,focusOffset:r.focusOffset}),Yl&&ii(Yl,r)||(Yl=r,r=uc(Af,"onSelect"),0<r.length&&(t=new yp("onSelect","select",null,t,n),e.push({event:t,listeners:r}),t.target=ya)))}function Ms(e,t){var n={};return n[e.toLowerCase()]=t.toLowerCase(),n["Webkit"+e]="webkit"+t,n["Moz"+e]="moz"+t,n}var wa={animationend:Ms("Animation","AnimationEnd"),animationiteration:Ms("Animation","AnimationIteration"),animationstart:Ms("Animation","AnimationStart"),transitionend:Ms("Transition","TransitionEnd")},nf={},fx={};br&&(fx=document.createElement("div").style,"AnimationEvent"in window||(delete wa.animationend.animation,delete wa.animationiteration.animation,delete wa.animationstart.animation),"TransitionEvent"in window||delete wa.transitionend.transition);function _c(e){if(nf[e])return nf[e];if(!wa[e])return e;var t=wa[e],n;for(n in t)if(t.hasOwnProperty(n)&&n in fx)return nf[e]=t[n];return e}var px=_c("animationend"),mx=_c("animationiteration"),vx=_c("animationstart"),gx=_c("transitionend"),hx=new Map,Hh="abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");function oo(e,t){hx.set(e,t),Ko(t,[e])}for(Ds=0;Ds<Hh.length;Ds++)zs=Hh[Ds],$h=zs.toLowerCase(),Uh=zs[0].toUpperCase()+zs.slice(1),oo($h,"on"+Uh);var zs,$h,Uh,Ds;oo(px,"onAnimationEnd");oo(mx,"onAnimationIteration");oo(vx,"onAnimationStart");oo("dblclick","onDoubleClick");oo("focusin","onFocus");oo("focusout","onBlur");oo(gx,"onTransitionEnd");Aa("onMouseEnter",["mouseout","mouseover"]);Aa("onMouseLeave",["mouseout","mouseover"]);Aa("onPointerEnter",["pointerout","pointerover"]);Aa("onPointerLeave",["pointerout","pointerover"]);Ko("onChange","change click focusin focusout input keydown keyup selectionchange".split(" "));Ko("onSelect","focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "));Ko("onBeforeInput",["compositionend","keypress","textInput","paste"]);Ko("onCompositionEnd","compositionend focusout keydown keypress keyup mousedown".split(" "));Ko("onCompositionStart","compositionstart focusout keydown keypress keyup mousedown".split(" "));Ko("onCompositionUpdate","compositionupdate focusout keydown keypress keyup mousedown".split(" "));var $l="abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "),MT=new Set("cancel close invalid load scroll toggle".split(" ").concat($l));function Kh(e,t,n){var r=e.type||"unknown-event";e.currentTarget=n,Mk(r,t,void 0,e),e.currentTarget=null}function bx(e,t){t=(t&4)!==0;for(var n=0;n<e.length;n++){var r=e[n],o=r.event;r=r.listeners;e:{var a=void 0;if(t)for(var l=r.length-1;0<=l;l--){var i=r[l],s=i.instance,c=i.currentTarget;if(i=i.listener,s!==a&&o.isPropagationStopped())break e;Kh(o,i,c),a=s}else for(l=0;l<r.length;l++){if(i=r[l],s=i.instance,c=i.currentTarget,i=i.listener,s!==a&&o.isPropagationStopped())break e;Kh(o,i,c),a=s}}}if(ac)throw e=Lf,ac=!1,Lf=null,e}function Ae(e,t){var n=t[jf];n===void 0&&(n=t[jf]=new Set);var r=e+"__bubble";n.has(r)||(xx(t,e,2,!1),n.add(r))}function rf(e,t,n){var r=0;t&&(r|=4),xx(n,e,r,t)}var Ws="_reactListening"+Math.random().toString(36).slice(2);function si(e){if(!e[Ws]){e[Ws]=!0,Tb.forEach(function(n){n!=="selectionchange"&&(MT.has(n)||rf(n,!1,e),rf(n,!0,e))});var t=e.nodeType===9?e:e.ownerDocument;t===null||t[Ws]||(t[Ws]=!0,rf("selectionchange",!1,t))}}function xx(e,t,n,r){switch(nx(t)){case 1:var o=Jk;break;case 4:o=eT;break;default:o=bp}n=o.bind(null,t,n,e),o=void 0,!_f||t!=="touchstart"&&t!=="touchmove"&&t!=="wheel"||(o=!0),r?o!==void 0?e.addEventListener(t,n,{capture:!0,passive:o}):e.addEventListener(t,n,!0):o!==void 0?e.addEventListener(t,n,{passive:o}):e.addEventListener(t,n,!1)}function of(e,t,n,r,o){var a=r;if((t&1)===0&&(t&2)===0&&r!==null)e:for(;;){if(r===null)return;var l=r.tag;if(l===3||l===4){var i=r.stateNode.containerInfo;if(i===o||i.nodeType===8&&i.parentNode===o)break;if(l===4)for(l=r.return;l!==null;){var s=l.tag;if((s===3||s===4)&&(s=l.stateNode.containerInfo,s===o||s.nodeType===8&&s.parentNode===o))return;l=l.return}for(;i!==null;){if(l=Fo(i),l===null)return;if(s=l.tag,s===5||s===6){r=a=l;continue e}i=i.parentNode}}r=r.return}Vb(function(){var c=a,d=mp(n),p=[];e:{var g=hx.get(e);if(g!==void 0){var m=yp,b=e;switch(e){case"keypress":if(Ys(n)===0)break e;case"keydown":case"keyup":m=vT;break;case"focusin":b="focus",m=ef;break;case"focusout":b="blur",m=ef;break;case"beforeblur":case"afterblur":m=ef;break;case"click":if(n.button===2)break e;case"auxclick":case"dblclick":case"mousedown":case"mousemove":case"mouseup":case"mouseout":case"mouseover":case"contextmenu":m=Nh;break;case"drag":case"dragend":case"dragenter":case"dragexit":case"dragleave":case"dragover":case"dragstart":case"drop":m=rT;break;case"touchcancel":case"touchend":case"touchmove":case"touchstart":m=bT;break;case px:case mx:case vx:m=lT;break;case gx:m=yT;break;case"scroll":m=tT;break;case"wheel":m=IT;break;case"copy":case"cut":case"paste":m=sT;break;case"gotpointercapture":case"lostpointercapture":case"pointercancel":case"pointerdown":case"pointermove":case"pointerout":case"pointerover":case"pointerup":m=Ah}var h=(t&4)!==0,y=!h&&e==="scroll",v=h?g!==null?g+"Capture":null:g;h=[];for(var u=c,f;u!==null;){f=u;var x=f.stateNode;if(f.tag===5&&x!==null&&(f=x,v!==null&&(x=ni(u,v),x!=null&&h.push(ci(u,x,f)))),y)break;u=u.return}0<h.length&&(g=new m(g,b,null,n,d),p.push({event:g,listeners:h}))}}if((t&7)===0){e:{if(g=e==="mouseover"||e==="pointerover",m=e==="mouseout"||e==="pointerout",g&&n!==Ef&&(b=n.relatedTarget||n.fromElement)&&(Fo(b)||b[xr]))break e;if((m||g)&&(g=d.window===d?d:(g=d.ownerDocument)?g.defaultView||g.parentWindow:window,m?(b=n.relatedTarget||n.toElement,m=c,b=b?Fo(b):null,b!==null&&(y=Go(b),b!==y||b.tag!==5&&b.tag!==6)&&(b=null)):(m=null,b=c),m!==b)){if(h=Nh,x="onMouseLeave",v="onMouseEnter",u="mouse",(e==="pointerout"||e==="pointerover")&&(h=Ah,x="onPointerLeave",v="onPointerEnter",u="pointer"),y=m==null?g:Ia(m),f=b==null?g:Ia(b),g=new h(x,u+"leave",m,n,d),g.target=y,g.relatedTarget=f,x=null,Fo(d)===c&&(h=new h(v,u+"enter",b,n,d),h.target=f,h.relatedTarget=y,x=h),y=x,m&&b)t:{for(h=m,v=b,u=0,f=h;f;f=ga(f))u++;for(f=0,x=v;x;x=ga(x))f++;for(;0<u-f;)h=ga(h),u--;for(;0<f-u;)v=ga(v),f--;for(;u--;){if(h===v||v!==null&&h===v.alternate)break t;h=ga(h),v=ga(v)}h=null}else h=null;m!==null&&Gh(p,g,m,h,!1),b!==null&&y!==null&&Gh(p,y,b,h,!0)}}e:{if(g=c?Ia(c):window,m=g.nodeName&&g.nodeName.toLowerCase(),m==="select"||m==="input"&&g.type==="file")var I=PT;else if(Dh(g))if(sx)I=NT;else{I=LT;var C=_T}else(m=g.nodeName)&&m.toLowerCase()==="input"&&(g.type==="checkbox"||g.type==="radio")&&(I=OT);if(I&&(I=I(e,c))){ix(p,I,n,d);break e}C&&C(e,g,c),e==="focusout"&&(C=g._wrapperState)&&C.controlled&&g.type==="number"&&Cf(g,"number",g.value)}switch(C=c?Ia(c):window,e){case"focusin":(Dh(C)||C.contentEditable==="true")&&(ya=C,Af=c,Yl=null);break;case"focusout":Yl=Af=ya=null;break;case"mousedown":Ff=!0;break;case"contextmenu":case"mouseup":case"dragend":Ff=!1,Vh(p,n,d);break;case"selectionchange":if(FT)break;case"keydown":case"keyup":Vh(p,n,d)}var k;if(Ip)e:{switch(e){case"compositionstart":var T="onCompositionStart";break e;case"compositionend":T="onCompositionEnd";break e;case"compositionupdate":T="onCompositionUpdate";break e}T=void 0}else xa?ax(e,n)&&(T="onCompositionEnd"):e==="keydown"&&n.keyCode===229&&(T="onCompositionStart");T&&(ox&&n.locale!=="ko"&&(xa||T!=="onCompositionStart"?T==="onCompositionEnd"&&xa&&(k=rx()):(Kr=d,xp="value"in Kr?Kr.value:Kr.textContent,xa=!0)),C=uc(c,T),0<C.length&&(T=new Bh(T,e,null,n,d),p.push({event:T,listeners:C}),k?T.data=k:(k=lx(n),k!==null&&(T.data=k)))),(k=ST?kT(e,n):TT(e,n))&&(c=uc(c,"onBeforeInput"),0<c.length&&(d=new Bh("onBeforeInput","beforeinput",null,n,d),p.push({event:d,listeners:c}),d.data=k))}bx(p,t)})}function ci(e,t,n){return{instance:e,listener:t,currentTarget:n}}function uc(e,t){for(var n=t+"Capture",r=[];e!==null;){var o=e,a=o.stateNode;o.tag===5&&a!==null&&(o=a,a=ni(e,n),a!=null&&r.unshift(ci(e,a,o)),a=ni(e,t),a!=null&&r.push(ci(e,a,o))),e=e.return}return r}function ga(e){if(e===null)return null;do e=e.return;while(e&&e.tag!==5);return e||null}function Gh(e,t,n,r,o){for(var a=t._reactName,l=[];n!==null&&n!==r;){var i=n,s=i.alternate,c=i.stateNode;if(s!==null&&s===r)break;i.tag===5&&c!==null&&(i=c,o?(s=ni(n,a),s!=null&&l.unshift(ci(n,s,i))):o||(s=ni(n,a),s!=null&&l.push(ci(n,s,i)))),n=n.return}l.length!==0&&e.push({event:t,listeners:l})}var DT=/\r\n?/g,zT=/\u0000|\uFFFD/g;function qh(e){return(typeof e=="string"?e:""+e).replace(DT,`
`).replace(zT,"")}function js(e,t,n){if(t=qh(t),qh(e)!==t&&n)throw Error(H(425))}function dc(){}var Mf=null,Df=null;function zf(e,t){return e==="textarea"||e==="noscript"||typeof t.children=="string"||typeof t.children=="number"||typeof t.dangerouslySetInnerHTML=="object"&&t.dangerouslySetInnerHTML!==null&&t.dangerouslySetInnerHTML.__html!=null}var Wf=typeof setTimeout=="function"?setTimeout:void 0,WT=typeof clearTimeout=="function"?clearTimeout:void 0,Yh=typeof Promise=="function"?Promise:void 0,jT=typeof queueMicrotask=="function"?queueMicrotask:typeof Yh<"u"?function(e){return Yh.resolve(null).then(e).catch(VT)}:Wf;function VT(e){setTimeout(function(){throw e})}function af(e,t){var n=t,r=0;do{var o=n.nextSibling;if(e.removeChild(n),o&&o.nodeType===8)if(n=o.data,n==="/$"){if(r===0){e.removeChild(o),ai(t);return}r--}else n!=="$"&&n!=="$?"&&n!=="$!"||r++;n=o}while(n);ai(t)}function Xr(e){for(;e!=null;e=e.nextSibling){var t=e.nodeType;if(t===1||t===3)break;if(t===8){if(t=e.data,t==="$"||t==="$!"||t==="$?")break;if(t==="/$")return null}}return e}function Qh(e){e=e.previousSibling;for(var t=0;e;){if(e.nodeType===8){var n=e.data;if(n==="$"||n==="$!"||n==="$?"){if(t===0)return e;t--}else n==="/$"&&t++}e=e.previousSibling}return null}var Ha=Math.random().toString(36).slice(2),qn="__reactFiber$"+Ha,ui="__reactProps$"+Ha,xr="__reactContainer$"+Ha,jf="__reactEvents$"+Ha,HT="__reactListeners$"+Ha,$T="__reactHandles$"+Ha;function Fo(e){var t=e[qn];if(t)return t;for(var n=e.parentNode;n;){if(t=n[xr]||n[qn]){if(n=t.alternate,t.child!==null||n!==null&&n.child!==null)for(e=Qh(e);e!==null;){if(n=e[qn])return n;e=Qh(e)}return t}e=n,n=e.parentNode}return null}function xi(e){return e=e[qn]||e[xr],!e||e.tag!==5&&e.tag!==6&&e.tag!==13&&e.tag!==3?null:e}function Ia(e){if(e.tag===5||e.tag===6)return e.stateNode;throw Error(H(33))}function Lc(e){return e[ui]||null}var Vf=[],Ca=-1;function ao(e){return{current:e}}function Fe(e){0>Ca||(e.current=Vf[Ca],Vf[Ca]=null,Ca--)}function Be(e,t){Ca++,Vf[Ca]=e.current,e.current=t}var ro={},wt=ao(ro),zt=ao(!1),jo=ro;function Fa(e,t){var n=e.type.contextTypes;if(!n)return ro;var r=e.stateNode;if(r&&r.__reactInternalMemoizedUnmaskedChildContext===t)return r.__reactInternalMemoizedMaskedChildContext;var o={},a;for(a in n)o[a]=t[a];return r&&(e=e.stateNode,e.__reactInternalMemoizedUnmaskedChildContext=t,e.__reactInternalMemoizedMaskedChildContext=o),o}function Wt(e){return e=e.childContextTypes,e!=null}function fc(){Fe(zt),Fe(wt)}function Xh(e,t,n){if(wt.current!==ro)throw Error(H(168));Be(wt,t),Be(zt,n)}function yx(e,t,n){var r=e.stateNode;if(t=t.childContextTypes,typeof r.getChildContext!="function")return n;r=r.getChildContext();for(var o in r)if(!(o in t))throw Error(H(108,_k(e)||"Unknown",o));return qe({},n,r)}function pc(e){return e=(e=e.stateNode)&&e.__reactInternalMemoizedMergedChildContext||ro,jo=wt.current,Be(wt,e),Be(zt,zt.current),!0}function Zh(e,t,n){var r=e.stateNode;if(!r)throw Error(H(169));n?(e=yx(e,t,jo),r.__reactInternalMemoizedMergedChildContext=e,Fe(zt),Fe(wt),Be(wt,e)):Fe(zt),Be(zt,n)}var mr=null,Oc=!1,lf=!1;function wx(e){mr===null?mr=[e]:mr.push(e)}function UT(e){Oc=!0,wx(e)}function lo(){if(!lf&&mr!==null){lf=!0;var e=0,t=Pe;try{var n=mr;for(Pe=1;e<n.length;e++){var r=n[e];do r=r(!0);while(r!==null)}mr=null,Oc=!1}catch(o){throw mr!==null&&(mr=mr.slice(e+1)),Kb(vp,lo),o}finally{Pe=t,lf=!1}}return null}var Sa=[],ka=0,mc=null,vc=0,sn=[],cn=0,Vo=null,vr=1,gr="";function Bo(e,t){Sa[ka++]=vc,Sa[ka++]=mc,mc=e,vc=t}function Ix(e,t,n){sn[cn++]=vr,sn[cn++]=gr,sn[cn++]=Vo,Vo=e;var r=vr;e=gr;var o=32-Rn(r)-1;r&=~(1<<o),n+=1;var a=32-Rn(t)+o;if(30<a){var l=o-o%5;a=(r&(1<<l)-1).toString(32),r>>=l,o-=l,vr=1<<32-Rn(t)+o|n<<o|r,gr=a+e}else vr=1<<a|n<<o|r,gr=e}function Sp(e){e.return!==null&&(Bo(e,1),Ix(e,1,0))}function kp(e){for(;e===mc;)mc=Sa[--ka],Sa[ka]=null,vc=Sa[--ka],Sa[ka]=null;for(;e===Vo;)Vo=sn[--cn],sn[cn]=null,gr=sn[--cn],sn[cn]=null,vr=sn[--cn],sn[cn]=null}var Kt=null,Ut=null,De=!1,Tn=null;function Cx(e,t){var n=un(5,null,null,0);n.elementType="DELETED",n.stateNode=t,n.return=e,t=e.deletions,t===null?(e.deletions=[n],e.flags|=16):t.push(n)}function Jh(e,t){switch(e.tag){case 5:var n=e.type;return t=t.nodeType!==1||n.toLowerCase()!==t.nodeName.toLowerCase()?null:t,t!==null?(e.stateNode=t,Kt=e,Ut=Xr(t.firstChild),!0):!1;case 6:return t=e.pendingProps===""||t.nodeType!==3?null:t,t!==null?(e.stateNode=t,Kt=e,Ut=null,!0):!1;case 13:return t=t.nodeType!==8?null:t,t!==null?(n=Vo!==null?{id:vr,overflow:gr}:null,e.memoizedState={dehydrated:t,treeContext:n,retryLane:1073741824},n=un(18,null,null,0),n.stateNode=t,n.return=e,e.child=n,Kt=e,Ut=null,!0):!1;default:return!1}}function Hf(e){return(e.mode&1)!==0&&(e.flags&128)===0}function $f(e){if(De){var t=Ut;if(t){var n=t;if(!Jh(e,t)){if(Hf(e))throw Error(H(418));t=Xr(n.nextSibling);var r=Kt;t&&Jh(e,t)?Cx(r,n):(e.flags=e.flags&-4097|2,De=!1,Kt=e)}}else{if(Hf(e))throw Error(H(418));e.flags=e.flags&-4097|2,De=!1,Kt=e}}}function eb(e){for(e=e.return;e!==null&&e.tag!==5&&e.tag!==3&&e.tag!==13;)e=e.return;Kt=e}function Vs(e){if(e!==Kt)return!1;if(!De)return eb(e),De=!0,!1;var t;if((t=e.tag!==3)&&!(t=e.tag!==5)&&(t=e.type,t=t!=="head"&&t!=="body"&&!zf(e.type,e.memoizedProps)),t&&(t=Ut)){if(Hf(e))throw Sx(),Error(H(418));for(;t;)Cx(e,t),t=Xr(t.nextSibling)}if(eb(e),e.tag===13){if(e=e.memoizedState,e=e!==null?e.dehydrated:null,!e)throw Error(H(317));e:{for(e=e.nextSibling,t=0;e;){if(e.nodeType===8){var n=e.data;if(n==="/$"){if(t===0){Ut=Xr(e.nextSibling);break e}t--}else n!=="$"&&n!=="$!"&&n!=="$?"||t++}e=e.nextSibling}Ut=null}}else Ut=Kt?Xr(e.stateNode.nextSibling):null;return!0}function Sx(){for(var e=Ut;e;)e=Xr(e.nextSibling)}function Ma(){Ut=Kt=null,De=!1}function Tp(e){Tn===null?Tn=[e]:Tn.push(e)}var KT=Ir.ReactCurrentBatchConfig;function Ml(e,t,n){if(e=n.ref,e!==null&&typeof e!="function"&&typeof e!="object"){if(n._owner){if(n=n._owner,n){if(n.tag!==1)throw Error(H(309));var r=n.stateNode}if(!r)throw Error(H(147,e));var o=r,a=""+e;return t!==null&&t.ref!==null&&typeof t.ref=="function"&&t.ref._stringRef===a?t.ref:(t=function(l){var i=o.refs;l===null?delete i[a]:i[a]=l},t._stringRef=a,t)}if(typeof e!="string")throw Error(H(284));if(!n._owner)throw Error(H(290,e))}return e}function Hs(e,t){throw e=Object.prototype.toString.call(t),Error(H(31,e==="[object Object]"?"object with keys {"+Object.keys(t).join(", ")+"}":e))}function tb(e){var t=e._init;return t(e._payload)}function kx(e){function t(v,u){if(e){var f=v.deletions;f===null?(v.deletions=[u],v.flags|=16):f.push(u)}}function n(v,u){if(!e)return null;for(;u!==null;)t(v,u),u=u.sibling;return null}function r(v,u){for(v=new Map;u!==null;)u.key!==null?v.set(u.key,u):v.set(u.index,u),u=u.sibling;return v}function o(v,u){return v=to(v,u),v.index=0,v.sibling=null,v}function a(v,u,f){return v.index=f,e?(f=v.alternate,f!==null?(f=f.index,f<u?(v.flags|=2,u):f):(v.flags|=2,u)):(v.flags|=1048576,u)}function l(v){return e&&v.alternate===null&&(v.flags|=2),v}function i(v,u,f,x){return u===null||u.tag!==6?(u=mf(f,v.mode,x),u.return=v,u):(u=o(u,f),u.return=v,u)}function s(v,u,f,x){var I=f.type;return I===ba?d(v,u,f.props.children,x,f.key):u!==null&&(u.elementType===I||typeof I=="object"&&I!==null&&I.$$typeof===Vr&&tb(I)===u.type)?(x=o(u,f.props),x.ref=Ml(v,u,f),x.return=v,x):(x=nc(f.type,f.key,f.props,null,v.mode,x),x.ref=Ml(v,u,f),x.return=v,x)}function c(v,u,f,x){return u===null||u.tag!==4||u.stateNode.containerInfo!==f.containerInfo||u.stateNode.implementation!==f.implementation?(u=vf(f,v.mode,x),u.return=v,u):(u=o(u,f.children||[]),u.return=v,u)}function d(v,u,f,x,I){return u===null||u.tag!==7?(u=Wo(f,v.mode,x,I),u.return=v,u):(u=o(u,f),u.return=v,u)}function p(v,u,f){if(typeof u=="string"&&u!==""||typeof u=="number")return u=mf(""+u,v.mode,f),u.return=v,u;if(typeof u=="object"&&u!==null){switch(u.$$typeof){case Es:return f=nc(u.type,u.key,u.props,null,v.mode,f),f.ref=Ml(v,null,u),f.return=v,f;case ha:return u=vf(u,v.mode,f),u.return=v,u;case Vr:var x=u._init;return p(v,x(u._payload),f)}if(Vl(u)||Nl(u))return u=Wo(u,v.mode,f,null),u.return=v,u;Hs(v,u)}return null}function g(v,u,f,x){var I=u!==null?u.key:null;if(typeof f=="string"&&f!==""||typeof f=="number")return I!==null?null:i(v,u,""+f,x);if(typeof f=="object"&&f!==null){switch(f.$$typeof){case Es:return f.key===I?s(v,u,f,x):null;case ha:return f.key===I?c(v,u,f,x):null;case Vr:return I=f._init,g(v,u,I(f._payload),x)}if(Vl(f)||Nl(f))return I!==null?null:d(v,u,f,x,null);Hs(v,f)}return null}function m(v,u,f,x,I){if(typeof x=="string"&&x!==""||typeof x=="number")return v=v.get(f)||null,i(u,v,""+x,I);if(typeof x=="object"&&x!==null){switch(x.$$typeof){case Es:return v=v.get(x.key===null?f:x.key)||null,s(u,v,x,I);case ha:return v=v.get(x.key===null?f:x.key)||null,c(u,v,x,I);case Vr:var C=x._init;return m(v,u,f,C(x._payload),I)}if(Vl(x)||Nl(x))return v=v.get(f)||null,d(u,v,x,I,null);Hs(u,x)}return null}function b(v,u,f,x){for(var I=null,C=null,k=u,T=u=0,z=null;k!==null&&T<f.length;T++){k.index>T?(z=k,k=null):z=k.sibling;var O=g(v,k,f[T],x);if(O===null){k===null&&(k=z);break}e&&k&&O.alternate===null&&t(v,k),u=a(O,u,T),C===null?I=O:C.sibling=O,C=O,k=z}if(T===f.length)return n(v,k),De&&Bo(v,T),I;if(k===null){for(;T<f.length;T++)k=p(v,f[T],x),k!==null&&(u=a(k,u,T),C===null?I=k:C.sibling=k,C=k);return De&&Bo(v,T),I}for(k=r(v,k);T<f.length;T++)z=m(k,v,T,f[T],x),z!==null&&(e&&z.alternate!==null&&k.delete(z.key===null?T:z.key),u=a(z,u,T),C===null?I=z:C.sibling=z,C=z);return e&&k.forEach(function(A){return t(v,A)}),De&&Bo(v,T),I}function h(v,u,f,x){var I=Nl(f);if(typeof I!="function")throw Error(H(150));if(f=I.call(f),f==null)throw Error(H(151));for(var C=I=null,k=u,T=u=0,z=null,O=f.next();k!==null&&!O.done;T++,O=f.next()){k.index>T?(z=k,k=null):z=k.sibling;var A=g(v,k,O.value,x);if(A===null){k===null&&(k=z);break}e&&k&&A.alternate===null&&t(v,k),u=a(A,u,T),C===null?I=A:C.sibling=A,C=A,k=z}if(O.done)return n(v,k),De&&Bo(v,T),I;if(k===null){for(;!O.done;T++,O=f.next())O=p(v,O.value,x),O!==null&&(u=a(O,u,T),C===null?I=O:C.sibling=O,C=O);return De&&Bo(v,T),I}for(k=r(v,k);!O.done;T++,O=f.next())O=m(k,v,T,O.value,x),O!==null&&(e&&O.alternate!==null&&k.delete(O.key===null?T:O.key),u=a(O,u,T),C===null?I=O:C.sibling=O,C=O);return e&&k.forEach(function(B){return t(v,B)}),De&&Bo(v,T),I}function y(v,u,f,x){if(typeof f=="object"&&f!==null&&f.type===ba&&f.key===null&&(f=f.props.children),typeof f=="object"&&f!==null){switch(f.$$typeof){case Es:e:{for(var I=f.key,C=u;C!==null;){if(C.key===I){if(I=f.type,I===ba){if(C.tag===7){n(v,C.sibling),u=o(C,f.props.children),u.return=v,v=u;break e}}else if(C.elementType===I||typeof I=="object"&&I!==null&&I.$$typeof===Vr&&tb(I)===C.type){n(v,C.sibling),u=o(C,f.props),u.ref=Ml(v,C,f),u.return=v,v=u;break e}n(v,C);break}else t(v,C);C=C.sibling}f.type===ba?(u=Wo(f.props.children,v.mode,x,f.key),u.return=v,v=u):(x=nc(f.type,f.key,f.props,null,v.mode,x),x.ref=Ml(v,u,f),x.return=v,v=x)}return l(v);case ha:e:{for(C=f.key;u!==null;){if(u.key===C)if(u.tag===4&&u.stateNode.containerInfo===f.containerInfo&&u.stateNode.implementation===f.implementation){n(v,u.sibling),u=o(u,f.children||[]),u.return=v,v=u;break e}else{n(v,u);break}else t(v,u);u=u.sibling}u=vf(f,v.mode,x),u.return=v,v=u}return l(v);case Vr:return C=f._init,y(v,u,C(f._payload),x)}if(Vl(f))return b(v,u,f,x);if(Nl(f))return h(v,u,f,x);Hs(v,f)}return typeof f=="string"&&f!==""||typeof f=="number"?(f=""+f,u!==null&&u.tag===6?(n(v,u.sibling),u=o(u,f),u.return=v,v=u):(n(v,u),u=mf(f,v.mode,x),u.return=v,v=u),l(v)):n(v,u)}return y}var Da=kx(!0),Tx=kx(!1),gc=ao(null),hc=null,Ta=null,Rp=null;function Ep(){Rp=Ta=hc=null}function Pp(e){var t=gc.current;Fe(gc),e._currentValue=t}function Uf(e,t,n){for(;e!==null;){var r=e.alternate;if((e.childLanes&t)!==t?(e.childLanes|=t,r!==null&&(r.childLanes|=t)):r!==null&&(r.childLanes&t)!==t&&(r.childLanes|=t),e===n)break;e=e.return}}function Na(e,t){hc=e,Rp=Ta=null,e=e.dependencies,e!==null&&e.firstContext!==null&&((e.lanes&t)!==0&&(Dt=!0),e.firstContext=null)}function fn(e){var t=e._currentValue;if(Rp!==e)if(e={context:e,memoizedValue:t,next:null},Ta===null){if(hc===null)throw Error(H(308));Ta=e,hc.dependencies={lanes:0,firstContext:e}}else Ta=Ta.next=e;return t}var Mo=null;function _p(e){Mo===null?Mo=[e]:Mo.push(e)}function Rx(e,t,n,r){var o=t.interleaved;return o===null?(n.next=n,_p(t)):(n.next=o.next,o.next=n),t.interleaved=n,yr(e,r)}function yr(e,t){e.lanes|=t;var n=e.alternate;for(n!==null&&(n.lanes|=t),n=e,e=e.return;e!==null;)e.childLanes|=t,n=e.alternate,n!==null&&(n.childLanes|=t),n=e,e=e.return;return n.tag===3?n.stateNode:null}var Hr=!1;function Lp(e){e.updateQueue={baseState:e.memoizedState,firstBaseUpdate:null,lastBaseUpdate:null,shared:{pending:null,interleaved:null,lanes:0},effects:null}}function Ex(e,t){e=e.updateQueue,t.updateQueue===e&&(t.updateQueue={baseState:e.baseState,firstBaseUpdate:e.firstBaseUpdate,lastBaseUpdate:e.lastBaseUpdate,shared:e.shared,effects:e.effects})}function hr(e,t){return{eventTime:e,lane:t,tag:0,payload:null,callback:null,next:null}}function Zr(e,t,n){var r=e.updateQueue;if(r===null)return null;if(r=r.shared,(Te&2)!==0){var o=r.pending;return o===null?t.next=t:(t.next=o.next,o.next=t),r.pending=t,yr(e,n)}return o=r.interleaved,o===null?(t.next=t,_p(r)):(t.next=o.next,o.next=t),r.interleaved=t,yr(e,n)}function Qs(e,t,n){if(t=t.updateQueue,t!==null&&(t=t.shared,(n&4194240)!==0)){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,gp(e,n)}}function nb(e,t){var n=e.updateQueue,r=e.alternate;if(r!==null&&(r=r.updateQueue,n===r)){var o=null,a=null;if(n=n.firstBaseUpdate,n!==null){do{var l={eventTime:n.eventTime,lane:n.lane,tag:n.tag,payload:n.payload,callback:n.callback,next:null};a===null?o=a=l:a=a.next=l,n=n.next}while(n!==null);a===null?o=a=t:a=a.next=t}else o=a=t;n={baseState:r.baseState,firstBaseUpdate:o,lastBaseUpdate:a,shared:r.shared,effects:r.effects},e.updateQueue=n;return}e=n.lastBaseUpdate,e===null?n.firstBaseUpdate=t:e.next=t,n.lastBaseUpdate=t}function bc(e,t,n,r){var o=e.updateQueue;Hr=!1;var a=o.firstBaseUpdate,l=o.lastBaseUpdate,i=o.shared.pending;if(i!==null){o.shared.pending=null;var s=i,c=s.next;s.next=null,l===null?a=c:l.next=c,l=s;var d=e.alternate;d!==null&&(d=d.updateQueue,i=d.lastBaseUpdate,i!==l&&(i===null?d.firstBaseUpdate=c:i.next=c,d.lastBaseUpdate=s))}if(a!==null){var p=o.baseState;l=0,d=c=s=null,i=a;do{var g=i.lane,m=i.eventTime;if((r&g)===g){d!==null&&(d=d.next={eventTime:m,lane:0,tag:i.tag,payload:i.payload,callback:i.callback,next:null});e:{var b=e,h=i;switch(g=t,m=n,h.tag){case 1:if(b=h.payload,typeof b=="function"){p=b.call(m,p,g);break e}p=b;break e;case 3:b.flags=b.flags&-65537|128;case 0:if(b=h.payload,g=typeof b=="function"?b.call(m,p,g):b,g==null)break e;p=qe({},p,g);break e;case 2:Hr=!0}}i.callback!==null&&i.lane!==0&&(e.flags|=64,g=o.effects,g===null?o.effects=[i]:g.push(i))}else m={eventTime:m,lane:g,tag:i.tag,payload:i.payload,callback:i.callback,next:null},d===null?(c=d=m,s=p):d=d.next=m,l|=g;if(i=i.next,i===null){if(i=o.shared.pending,i===null)break;g=i,i=g.next,g.next=null,o.lastBaseUpdate=g,o.shared.pending=null}}while(!0);if(d===null&&(s=p),o.baseState=s,o.firstBaseUpdate=c,o.lastBaseUpdate=d,t=o.shared.interleaved,t!==null){o=t;do l|=o.lane,o=o.next;while(o!==t)}else a===null&&(o.shared.lanes=0);$o|=l,e.lanes=l,e.memoizedState=p}}function rb(e,t,n){if(e=t.effects,t.effects=null,e!==null)for(t=0;t<e.length;t++){var r=e[t],o=r.callback;if(o!==null){if(r.callback=null,r=n,typeof o!="function")throw Error(H(191,o));o.call(r)}}}var yi={},Qn=ao(yi),di=ao(yi),fi=ao(yi);function Do(e){if(e===yi)throw Error(H(174));return e}function Op(e,t){switch(Be(fi,t),Be(di,e),Be(Qn,yi),e=t.nodeType,e){case 9:case 11:t=(t=t.documentElement)?t.namespaceURI:kf(null,"");break;default:e=e===8?t.parentNode:t,t=e.namespaceURI||null,e=e.tagName,t=kf(t,e)}Fe(Qn),Be(Qn,t)}function za(){Fe(Qn),Fe(di),Fe(fi)}function Px(e){Do(fi.current);var t=Do(Qn.current),n=kf(t,e.type);t!==n&&(Be(di,e),Be(Qn,n))}function Np(e){di.current===e&&(Fe(Qn),Fe(di))}var Ke=ao(0);function xc(e){for(var t=e;t!==null;){if(t.tag===13){var n=t.memoizedState;if(n!==null&&(n=n.dehydrated,n===null||n.data==="$?"||n.data==="$!"))return t}else if(t.tag===19&&t.memoizedProps.revealOrder!==void 0){if((t.flags&128)!==0)return t}else if(t.child!==null){t.child.return=t,t=t.child;continue}if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return null;t=t.return}t.sibling.return=t.return,t=t.sibling}return null}var sf=[];function Bp(){for(var e=0;e<sf.length;e++)sf[e]._workInProgressVersionPrimary=null;sf.length=0}var Xs=Ir.ReactCurrentDispatcher,cf=Ir.ReactCurrentBatchConfig,Ho=0,Ge=null,at=null,st=null,yc=!1,Ql=!1,pi=0,GT=0;function bt(){throw Error(H(321))}function Ap(e,t){if(t===null)return!1;for(var n=0;n<t.length&&n<e.length;n++)if(!Pn(e[n],t[n]))return!1;return!0}function Fp(e,t,n,r,o,a){if(Ho=a,Ge=t,t.memoizedState=null,t.updateQueue=null,t.lanes=0,Xs.current=e===null||e.memoizedState===null?XT:ZT,e=n(r,o),Ql){a=0;do{if(Ql=!1,pi=0,25<=a)throw Error(H(301));a+=1,st=at=null,t.updateQueue=null,Xs.current=JT,e=n(r,o)}while(Ql)}if(Xs.current=wc,t=at!==null&&at.next!==null,Ho=0,st=at=Ge=null,yc=!1,t)throw Error(H(300));return e}function Mp(){var e=pi!==0;return pi=0,e}function Gn(){var e={memoizedState:null,baseState:null,baseQueue:null,queue:null,next:null};return st===null?Ge.memoizedState=st=e:st=st.next=e,st}function pn(){if(at===null){var e=Ge.alternate;e=e!==null?e.memoizedState:null}else e=at.next;var t=st===null?Ge.memoizedState:st.next;if(t!==null)st=t,at=e;else{if(e===null)throw Error(H(310));at=e,e={memoizedState:at.memoizedState,baseState:at.baseState,baseQueue:at.baseQueue,queue:at.queue,next:null},st===null?Ge.memoizedState=st=e:st=st.next=e}return st}function mi(e,t){return typeof t=="function"?t(e):t}function uf(e){var t=pn(),n=t.queue;if(n===null)throw Error(H(311));n.lastRenderedReducer=e;var r=at,o=r.baseQueue,a=n.pending;if(a!==null){if(o!==null){var l=o.next;o.next=a.next,a.next=l}r.baseQueue=o=a,n.pending=null}if(o!==null){a=o.next,r=r.baseState;var i=l=null,s=null,c=a;do{var d=c.lane;if((Ho&d)===d)s!==null&&(s=s.next={lane:0,action:c.action,hasEagerState:c.hasEagerState,eagerState:c.eagerState,next:null}),r=c.hasEagerState?c.eagerState:e(r,c.action);else{var p={lane:d,action:c.action,hasEagerState:c.hasEagerState,eagerState:c.eagerState,next:null};s===null?(i=s=p,l=r):s=s.next=p,Ge.lanes|=d,$o|=d}c=c.next}while(c!==null&&c!==a);s===null?l=r:s.next=i,Pn(r,t.memoizedState)||(Dt=!0),t.memoizedState=r,t.baseState=l,t.baseQueue=s,n.lastRenderedState=r}if(e=n.interleaved,e!==null){o=e;do a=o.lane,Ge.lanes|=a,$o|=a,o=o.next;while(o!==e)}else o===null&&(n.lanes=0);return[t.memoizedState,n.dispatch]}function df(e){var t=pn(),n=t.queue;if(n===null)throw Error(H(311));n.lastRenderedReducer=e;var r=n.dispatch,o=n.pending,a=t.memoizedState;if(o!==null){n.pending=null;var l=o=o.next;do a=e(a,l.action),l=l.next;while(l!==o);Pn(a,t.memoizedState)||(Dt=!0),t.memoizedState=a,t.baseQueue===null&&(t.baseState=a),n.lastRenderedState=a}return[a,r]}function _x(){}function Lx(e,t){var n=Ge,r=pn(),o=t(),a=!Pn(r.memoizedState,o);if(a&&(r.memoizedState=o,Dt=!0),r=r.queue,Dp(Bx.bind(null,n,r,e),[e]),r.getSnapshot!==t||a||st!==null&&st.memoizedState.tag&1){if(n.flags|=2048,vi(9,Nx.bind(null,n,r,o,t),void 0,null),ct===null)throw Error(H(349));(Ho&30)!==0||Ox(n,t,o)}return o}function Ox(e,t,n){e.flags|=16384,e={getSnapshot:t,value:n},t=Ge.updateQueue,t===null?(t={lastEffect:null,stores:null},Ge.updateQueue=t,t.stores=[e]):(n=t.stores,n===null?t.stores=[e]:n.push(e))}function Nx(e,t,n,r){t.value=n,t.getSnapshot=r,Ax(t)&&Fx(e)}function Bx(e,t,n){return n(function(){Ax(t)&&Fx(e)})}function Ax(e){var t=e.getSnapshot;e=e.value;try{var n=t();return!Pn(e,n)}catch{return!0}}function Fx(e){var t=yr(e,1);t!==null&&En(t,e,1,-1)}function ob(e){var t=Gn();return typeof e=="function"&&(e=e()),t.memoizedState=t.baseState=e,e={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:mi,lastRenderedState:e},t.queue=e,e=e.dispatch=QT.bind(null,Ge,e),[t.memoizedState,e]}function vi(e,t,n,r){return e={tag:e,create:t,destroy:n,deps:r,next:null},t=Ge.updateQueue,t===null?(t={lastEffect:null,stores:null},Ge.updateQueue=t,t.lastEffect=e.next=e):(n=t.lastEffect,n===null?t.lastEffect=e.next=e:(r=n.next,n.next=e,e.next=r,t.lastEffect=e)),e}function Mx(){return pn().memoizedState}function Zs(e,t,n,r){var o=Gn();Ge.flags|=e,o.memoizedState=vi(1|t,n,void 0,r===void 0?null:r)}function Nc(e,t,n,r){var o=pn();r=r===void 0?null:r;var a=void 0;if(at!==null){var l=at.memoizedState;if(a=l.destroy,r!==null&&Ap(r,l.deps)){o.memoizedState=vi(t,n,a,r);return}}Ge.flags|=e,o.memoizedState=vi(1|t,n,a,r)}function ab(e,t){return Zs(8390656,8,e,t)}function Dp(e,t){return Nc(2048,8,e,t)}function Dx(e,t){return Nc(4,2,e,t)}function zx(e,t){return Nc(4,4,e,t)}function Wx(e,t){if(typeof t=="function")return e=e(),t(e),function(){t(null)};if(t!=null)return e=e(),t.current=e,function(){t.current=null}}function jx(e,t,n){return n=n!=null?n.concat([e]):null,Nc(4,4,Wx.bind(null,t,e),n)}function zp(){}function Vx(e,t){var n=pn();t=t===void 0?null:t;var r=n.memoizedState;return r!==null&&t!==null&&Ap(t,r[1])?r[0]:(n.memoizedState=[e,t],e)}function Hx(e,t){var n=pn();t=t===void 0?null:t;var r=n.memoizedState;return r!==null&&t!==null&&Ap(t,r[1])?r[0]:(e=e(),n.memoizedState=[e,t],e)}function $x(e,t,n){return(Ho&21)===0?(e.baseState&&(e.baseState=!1,Dt=!0),e.memoizedState=n):(Pn(n,t)||(n=Yb(),Ge.lanes|=n,$o|=n,e.baseState=!0),t)}function qT(e,t){var n=Pe;Pe=n!==0&&4>n?n:4,e(!0);var r=cf.transition;cf.transition={};try{e(!1),t()}finally{Pe=n,cf.transition=r}}function Ux(){return pn().memoizedState}function YT(e,t,n){var r=eo(e);if(n={lane:r,action:n,hasEagerState:!1,eagerState:null,next:null},Kx(e))Gx(t,n);else if(n=Rx(e,t,n,r),n!==null){var o=_t();En(n,e,r,o),qx(n,t,r)}}function QT(e,t,n){var r=eo(e),o={lane:r,action:n,hasEagerState:!1,eagerState:null,next:null};if(Kx(e))Gx(t,o);else{var a=e.alternate;if(e.lanes===0&&(a===null||a.lanes===0)&&(a=t.lastRenderedReducer,a!==null))try{var l=t.lastRenderedState,i=a(l,n);if(o.hasEagerState=!0,o.eagerState=i,Pn(i,l)){var s=t.interleaved;s===null?(o.next=o,_p(t)):(o.next=s.next,s.next=o),t.interleaved=o;return}}catch{}finally{}n=Rx(e,t,o,r),n!==null&&(o=_t(),En(n,e,r,o),qx(n,t,r))}}function Kx(e){var t=e.alternate;return e===Ge||t!==null&&t===Ge}function Gx(e,t){Ql=yc=!0;var n=e.pending;n===null?t.next=t:(t.next=n.next,n.next=t),e.pending=t}function qx(e,t,n){if((n&4194240)!==0){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,gp(e,n)}}var wc={readContext:fn,useCallback:bt,useContext:bt,useEffect:bt,useImperativeHandle:bt,useInsertionEffect:bt,useLayoutEffect:bt,useMemo:bt,useReducer:bt,useRef:bt,useState:bt,useDebugValue:bt,useDeferredValue:bt,useTransition:bt,useMutableSource:bt,useSyncExternalStore:bt,useId:bt,unstable_isNewReconciler:!1},XT={readContext:fn,useCallback:function(e,t){return Gn().memoizedState=[e,t===void 0?null:t],e},useContext:fn,useEffect:ab,useImperativeHandle:function(e,t,n){return n=n!=null?n.concat([e]):null,Zs(4194308,4,Wx.bind(null,t,e),n)},useLayoutEffect:function(e,t){return Zs(4194308,4,e,t)},useInsertionEffect:function(e,t){return Zs(4,2,e,t)},useMemo:function(e,t){var n=Gn();return t=t===void 0?null:t,e=e(),n.memoizedState=[e,t],e},useReducer:function(e,t,n){var r=Gn();return t=n!==void 0?n(t):t,r.memoizedState=r.baseState=t,e={pending:null,interleaved:null,lanes:0,dispatch:null,lastRenderedReducer:e,lastRenderedState:t},r.queue=e,e=e.dispatch=YT.bind(null,Ge,e),[r.memoizedState,e]},useRef:function(e){var t=Gn();return e={current:e},t.memoizedState=e},useState:ob,useDebugValue:zp,useDeferredValue:function(e){return Gn().memoizedState=e},useTransition:function(){var e=ob(!1),t=e[0];return e=qT.bind(null,e[1]),Gn().memoizedState=e,[t,e]},useMutableSource:function(){},useSyncExternalStore:function(e,t,n){var r=Ge,o=Gn();if(De){if(n===void 0)throw Error(H(407));n=n()}else{if(n=t(),ct===null)throw Error(H(349));(Ho&30)!==0||Ox(r,t,n)}o.memoizedState=n;var a={value:n,getSnapshot:t};return o.queue=a,ab(Bx.bind(null,r,a,e),[e]),r.flags|=2048,vi(9,Nx.bind(null,r,a,n,t),void 0,null),n},useId:function(){var e=Gn(),t=ct.identifierPrefix;if(De){var n=gr,r=vr;n=(r&~(1<<32-Rn(r)-1)).toString(32)+n,t=":"+t+"R"+n,n=pi++,0<n&&(t+="H"+n.toString(32)),t+=":"}else n=GT++,t=":"+t+"r"+n.toString(32)+":";return e.memoizedState=t},unstable_isNewReconciler:!1},ZT={readContext:fn,useCallback:Vx,useContext:fn,useEffect:Dp,useImperativeHandle:jx,useInsertionEffect:Dx,useLayoutEffect:zx,useMemo:Hx,useReducer:uf,useRef:Mx,useState:function(){return uf(mi)},useDebugValue:zp,useDeferredValue:function(e){var t=pn();return $x(t,at.memoizedState,e)},useTransition:function(){var e=uf(mi)[0],t=pn().memoizedState;return[e,t]},useMutableSource:_x,useSyncExternalStore:Lx,useId:Ux,unstable_isNewReconciler:!1},JT={readContext:fn,useCallback:Vx,useContext:fn,useEffect:Dp,useImperativeHandle:jx,useInsertionEffect:Dx,useLayoutEffect:zx,useMemo:Hx,useReducer:df,useRef:Mx,useState:function(){return df(mi)},useDebugValue:zp,useDeferredValue:function(e){var t=pn();return at===null?t.memoizedState=e:$x(t,at.memoizedState,e)},useTransition:function(){var e=df(mi)[0],t=pn().memoizedState;return[e,t]},useMutableSource:_x,useSyncExternalStore:Lx,useId:Ux,unstable_isNewReconciler:!1};function Sn(e,t){if(e&&e.defaultProps){t=qe({},t),e=e.defaultProps;for(var n in e)t[n]===void 0&&(t[n]=e[n]);return t}return t}function Kf(e,t,n,r){t=e.memoizedState,n=n(r,t),n=n==null?t:qe({},t,n),e.memoizedState=n,e.lanes===0&&(e.updateQueue.baseState=n)}var Bc={isMounted:function(e){return(e=e._reactInternals)?Go(e)===e:!1},enqueueSetState:function(e,t,n){e=e._reactInternals;var r=_t(),o=eo(e),a=hr(r,o);a.payload=t,n!=null&&(a.callback=n),t=Zr(e,a,o),t!==null&&(En(t,e,o,r),Qs(t,e,o))},enqueueReplaceState:function(e,t,n){e=e._reactInternals;var r=_t(),o=eo(e),a=hr(r,o);a.tag=1,a.payload=t,n!=null&&(a.callback=n),t=Zr(e,a,o),t!==null&&(En(t,e,o,r),Qs(t,e,o))},enqueueForceUpdate:function(e,t){e=e._reactInternals;var n=_t(),r=eo(e),o=hr(n,r);o.tag=2,t!=null&&(o.callback=t),t=Zr(e,o,r),t!==null&&(En(t,e,r,n),Qs(t,e,r))}};function lb(e,t,n,r,o,a,l){return e=e.stateNode,typeof e.shouldComponentUpdate=="function"?e.shouldComponentUpdate(r,a,l):t.prototype&&t.prototype.isPureReactComponent?!ii(n,r)||!ii(o,a):!0}function Yx(e,t,n){var r=!1,o=ro,a=t.contextType;return typeof a=="object"&&a!==null?a=fn(a):(o=Wt(t)?jo:wt.current,r=t.contextTypes,a=(r=r!=null)?Fa(e,o):ro),t=new t(n,a),e.memoizedState=t.state!==null&&t.state!==void 0?t.state:null,t.updater=Bc,e.stateNode=t,t._reactInternals=e,r&&(e=e.stateNode,e.__reactInternalMemoizedUnmaskedChildContext=o,e.__reactInternalMemoizedMaskedChildContext=a),t}function ib(e,t,n,r){e=t.state,typeof t.componentWillReceiveProps=="function"&&t.componentWillReceiveProps(n,r),typeof t.UNSAFE_componentWillReceiveProps=="function"&&t.UNSAFE_componentWillReceiveProps(n,r),t.state!==e&&Bc.enqueueReplaceState(t,t.state,null)}function Gf(e,t,n,r){var o=e.stateNode;o.props=n,o.state=e.memoizedState,o.refs={},Lp(e);var a=t.contextType;typeof a=="object"&&a!==null?o.context=fn(a):(a=Wt(t)?jo:wt.current,o.context=Fa(e,a)),o.state=e.memoizedState,a=t.getDerivedStateFromProps,typeof a=="function"&&(Kf(e,t,a,n),o.state=e.memoizedState),typeof t.getDerivedStateFromProps=="function"||typeof o.getSnapshotBeforeUpdate=="function"||typeof o.UNSAFE_componentWillMount!="function"&&typeof o.componentWillMount!="function"||(t=o.state,typeof o.componentWillMount=="function"&&o.componentWillMount(),typeof o.UNSAFE_componentWillMount=="function"&&o.UNSAFE_componentWillMount(),t!==o.state&&Bc.enqueueReplaceState(o,o.state,null),bc(e,n,o,r),o.state=e.memoizedState),typeof o.componentDidMount=="function"&&(e.flags|=4194308)}function Wa(e,t){try{var n="",r=t;do n+=Pk(r),r=r.return;while(r);var o=n}catch(a){o=`
Error generating stack: `+a.message+`
`+a.stack}return{value:e,source:t,stack:o,digest:null}}function ff(e,t,n){return{value:e,source:null,stack:n??null,digest:t??null}}function qf(e,t){try{console.error(t.value)}catch(n){setTimeout(function(){throw n})}}var eR=typeof WeakMap=="function"?WeakMap:Map;function Qx(e,t,n){n=hr(-1,n),n.tag=3,n.payload={element:null};var r=t.value;return n.callback=function(){Cc||(Cc=!0,op=r),qf(e,t)},n}function Xx(e,t,n){n=hr(-1,n),n.tag=3;var r=e.type.getDerivedStateFromError;if(typeof r=="function"){var o=t.value;n.payload=function(){return r(o)},n.callback=function(){qf(e,t)}}var a=e.stateNode;return a!==null&&typeof a.componentDidCatch=="function"&&(n.callback=function(){qf(e,t),typeof r!="function"&&(Jr===null?Jr=new Set([this]):Jr.add(this));var l=t.stack;this.componentDidCatch(t.value,{componentStack:l!==null?l:""})}),n}function sb(e,t,n){var r=e.pingCache;if(r===null){r=e.pingCache=new eR;var o=new Set;r.set(t,o)}else o=r.get(t),o===void 0&&(o=new Set,r.set(t,o));o.has(n)||(o.add(n),e=mR.bind(null,e,t,n),t.then(e,e))}function cb(e){do{var t;if((t=e.tag===13)&&(t=e.memoizedState,t=t!==null?t.dehydrated!==null:!0),t)return e;e=e.return}while(e!==null);return null}function ub(e,t,n,r,o){return(e.mode&1)===0?(e===t?e.flags|=65536:(e.flags|=128,n.flags|=131072,n.flags&=-52805,n.tag===1&&(n.alternate===null?n.tag=17:(t=hr(-1,1),t.tag=2,Zr(n,t,1))),n.lanes|=1),e):(e.flags|=65536,e.lanes=o,e)}var tR=Ir.ReactCurrentOwner,Dt=!1;function Pt(e,t,n,r){t.child=e===null?Tx(t,null,n,r):Da(t,e.child,n,r)}function db(e,t,n,r,o){n=n.render;var a=t.ref;return Na(t,o),r=Fp(e,t,n,r,a,o),n=Mp(),e!==null&&!Dt?(t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~o,wr(e,t,o)):(De&&n&&Sp(t),t.flags|=1,Pt(e,t,r,o),t.child)}function fb(e,t,n,r,o){if(e===null){var a=n.type;return typeof a=="function"&&!Gp(a)&&a.defaultProps===void 0&&n.compare===null&&n.defaultProps===void 0?(t.tag=15,t.type=a,Zx(e,t,a,r,o)):(e=nc(n.type,null,r,t,t.mode,o),e.ref=t.ref,e.return=t,t.child=e)}if(a=e.child,(e.lanes&o)===0){var l=a.memoizedProps;if(n=n.compare,n=n!==null?n:ii,n(l,r)&&e.ref===t.ref)return wr(e,t,o)}return t.flags|=1,e=to(a,r),e.ref=t.ref,e.return=t,t.child=e}function Zx(e,t,n,r,o){if(e!==null){var a=e.memoizedProps;if(ii(a,r)&&e.ref===t.ref)if(Dt=!1,t.pendingProps=r=a,(e.lanes&o)!==0)(e.flags&131072)!==0&&(Dt=!0);else return t.lanes=e.lanes,wr(e,t,o)}return Yf(e,t,n,r,o)}function Jx(e,t,n){var r=t.pendingProps,o=r.children,a=e!==null?e.memoizedState:null;if(r.mode==="hidden")if((t.mode&1)===0)t.memoizedState={baseLanes:0,cachePool:null,transitions:null},Be(Ea,$t),$t|=n;else{if((n&1073741824)===0)return e=a!==null?a.baseLanes|n:n,t.lanes=t.childLanes=1073741824,t.memoizedState={baseLanes:e,cachePool:null,transitions:null},t.updateQueue=null,Be(Ea,$t),$t|=e,null;t.memoizedState={baseLanes:0,cachePool:null,transitions:null},r=a!==null?a.baseLanes:n,Be(Ea,$t),$t|=r}else a!==null?(r=a.baseLanes|n,t.memoizedState=null):r=n,Be(Ea,$t),$t|=r;return Pt(e,t,o,n),t.child}function ey(e,t){var n=t.ref;(e===null&&n!==null||e!==null&&e.ref!==n)&&(t.flags|=512,t.flags|=2097152)}function Yf(e,t,n,r,o){var a=Wt(n)?jo:wt.current;return a=Fa(t,a),Na(t,o),n=Fp(e,t,n,r,a,o),r=Mp(),e!==null&&!Dt?(t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~o,wr(e,t,o)):(De&&r&&Sp(t),t.flags|=1,Pt(e,t,n,o),t.child)}function pb(e,t,n,r,o){if(Wt(n)){var a=!0;pc(t)}else a=!1;if(Na(t,o),t.stateNode===null)Js(e,t),Yx(t,n,r),Gf(t,n,r,o),r=!0;else if(e===null){var l=t.stateNode,i=t.memoizedProps;l.props=i;var s=l.context,c=n.contextType;typeof c=="object"&&c!==null?c=fn(c):(c=Wt(n)?jo:wt.current,c=Fa(t,c));var d=n.getDerivedStateFromProps,p=typeof d=="function"||typeof l.getSnapshotBeforeUpdate=="function";p||typeof l.UNSAFE_componentWillReceiveProps!="function"&&typeof l.componentWillReceiveProps!="function"||(i!==r||s!==c)&&ib(t,l,r,c),Hr=!1;var g=t.memoizedState;l.state=g,bc(t,r,l,o),s=t.memoizedState,i!==r||g!==s||zt.current||Hr?(typeof d=="function"&&(Kf(t,n,d,r),s=t.memoizedState),(i=Hr||lb(t,n,i,r,g,s,c))?(p||typeof l.UNSAFE_componentWillMount!="function"&&typeof l.componentWillMount!="function"||(typeof l.componentWillMount=="function"&&l.componentWillMount(),typeof l.UNSAFE_componentWillMount=="function"&&l.UNSAFE_componentWillMount()),typeof l.componentDidMount=="function"&&(t.flags|=4194308)):(typeof l.componentDidMount=="function"&&(t.flags|=4194308),t.memoizedProps=r,t.memoizedState=s),l.props=r,l.state=s,l.context=c,r=i):(typeof l.componentDidMount=="function"&&(t.flags|=4194308),r=!1)}else{l=t.stateNode,Ex(e,t),i=t.memoizedProps,c=t.type===t.elementType?i:Sn(t.type,i),l.props=c,p=t.pendingProps,g=l.context,s=n.contextType,typeof s=="object"&&s!==null?s=fn(s):(s=Wt(n)?jo:wt.current,s=Fa(t,s));var m=n.getDerivedStateFromProps;(d=typeof m=="function"||typeof l.getSnapshotBeforeUpdate=="function")||typeof l.UNSAFE_componentWillReceiveProps!="function"&&typeof l.componentWillReceiveProps!="function"||(i!==p||g!==s)&&ib(t,l,r,s),Hr=!1,g=t.memoizedState,l.state=g,bc(t,r,l,o);var b=t.memoizedState;i!==p||g!==b||zt.current||Hr?(typeof m=="function"&&(Kf(t,n,m,r),b=t.memoizedState),(c=Hr||lb(t,n,c,r,g,b,s)||!1)?(d||typeof l.UNSAFE_componentWillUpdate!="function"&&typeof l.componentWillUpdate!="function"||(typeof l.componentWillUpdate=="function"&&l.componentWillUpdate(r,b,s),typeof l.UNSAFE_componentWillUpdate=="function"&&l.UNSAFE_componentWillUpdate(r,b,s)),typeof l.componentDidUpdate=="function"&&(t.flags|=4),typeof l.getSnapshotBeforeUpdate=="function"&&(t.flags|=1024)):(typeof l.componentDidUpdate!="function"||i===e.memoizedProps&&g===e.memoizedState||(t.flags|=4),typeof l.getSnapshotBeforeUpdate!="function"||i===e.memoizedProps&&g===e.memoizedState||(t.flags|=1024),t.memoizedProps=r,t.memoizedState=b),l.props=r,l.state=b,l.context=s,r=c):(typeof l.componentDidUpdate!="function"||i===e.memoizedProps&&g===e.memoizedState||(t.flags|=4),typeof l.getSnapshotBeforeUpdate!="function"||i===e.memoizedProps&&g===e.memoizedState||(t.flags|=1024),r=!1)}return Qf(e,t,n,r,a,o)}function Qf(e,t,n,r,o,a){ey(e,t);var l=(t.flags&128)!==0;if(!r&&!l)return o&&Zh(t,n,!1),wr(e,t,a);r=t.stateNode,tR.current=t;var i=l&&typeof n.getDerivedStateFromError!="function"?null:r.render();return t.flags|=1,e!==null&&l?(t.child=Da(t,e.child,null,a),t.child=Da(t,null,i,a)):Pt(e,t,i,a),t.memoizedState=r.state,o&&Zh(t,n,!0),t.child}function ty(e){var t=e.stateNode;t.pendingContext?Xh(e,t.pendingContext,t.pendingContext!==t.context):t.context&&Xh(e,t.context,!1),Op(e,t.containerInfo)}function mb(e,t,n,r,o){return Ma(),Tp(o),t.flags|=256,Pt(e,t,n,r),t.child}var Xf={dehydrated:null,treeContext:null,retryLane:0};function Zf(e){return{baseLanes:e,cachePool:null,transitions:null}}function ny(e,t,n){var r=t.pendingProps,o=Ke.current,a=!1,l=(t.flags&128)!==0,i;if((i=l)||(i=e!==null&&e.memoizedState===null?!1:(o&2)!==0),i?(a=!0,t.flags&=-129):(e===null||e.memoizedState!==null)&&(o|=1),Be(Ke,o&1),e===null)return $f(t),e=t.memoizedState,e!==null&&(e=e.dehydrated,e!==null)?((t.mode&1)===0?t.lanes=1:e.data==="$!"?t.lanes=8:t.lanes=1073741824,null):(l=r.children,e=r.fallback,a?(r=t.mode,a=t.child,l={mode:"hidden",children:l},(r&1)===0&&a!==null?(a.childLanes=0,a.pendingProps=l):a=Mc(l,r,0,null),e=Wo(e,r,n,null),a.return=t,e.return=t,a.sibling=e,t.child=a,t.child.memoizedState=Zf(n),t.memoizedState=Xf,e):Wp(t,l));if(o=e.memoizedState,o!==null&&(i=o.dehydrated,i!==null))return nR(e,t,l,r,i,o,n);if(a){a=r.fallback,l=t.mode,o=e.child,i=o.sibling;var s={mode:"hidden",children:r.children};return(l&1)===0&&t.child!==o?(r=t.child,r.childLanes=0,r.pendingProps=s,t.deletions=null):(r=to(o,s),r.subtreeFlags=o.subtreeFlags&14680064),i!==null?a=to(i,a):(a=Wo(a,l,n,null),a.flags|=2),a.return=t,r.return=t,r.sibling=a,t.child=r,r=a,a=t.child,l=e.child.memoizedState,l=l===null?Zf(n):{baseLanes:l.baseLanes|n,cachePool:null,transitions:l.transitions},a.memoizedState=l,a.childLanes=e.childLanes&~n,t.memoizedState=Xf,r}return a=e.child,e=a.sibling,r=to(a,{mode:"visible",children:r.children}),(t.mode&1)===0&&(r.lanes=n),r.return=t,r.sibling=null,e!==null&&(n=t.deletions,n===null?(t.deletions=[e],t.flags|=16):n.push(e)),t.child=r,t.memoizedState=null,r}function Wp(e,t){return t=Mc({mode:"visible",children:t},e.mode,0,null),t.return=e,e.child=t}function $s(e,t,n,r){return r!==null&&Tp(r),Da(t,e.child,null,n),e=Wp(t,t.pendingProps.children),e.flags|=2,t.memoizedState=null,e}function nR(e,t,n,r,o,a,l){if(n)return t.flags&256?(t.flags&=-257,r=ff(Error(H(422))),$s(e,t,l,r)):t.memoizedState!==null?(t.child=e.child,t.flags|=128,null):(a=r.fallback,o=t.mode,r=Mc({mode:"visible",children:r.children},o,0,null),a=Wo(a,o,l,null),a.flags|=2,r.return=t,a.return=t,r.sibling=a,t.child=r,(t.mode&1)!==0&&Da(t,e.child,null,l),t.child.memoizedState=Zf(l),t.memoizedState=Xf,a);if((t.mode&1)===0)return $s(e,t,l,null);if(o.data==="$!"){if(r=o.nextSibling&&o.nextSibling.dataset,r)var i=r.dgst;return r=i,a=Error(H(419)),r=ff(a,r,void 0),$s(e,t,l,r)}if(i=(l&e.childLanes)!==0,Dt||i){if(r=ct,r!==null){switch(l&-l){case 4:o=2;break;case 16:o=8;break;case 64:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:case 4194304:case 8388608:case 16777216:case 33554432:case 67108864:o=32;break;case 536870912:o=268435456;break;default:o=0}o=(o&(r.suspendedLanes|l))!==0?0:o,o!==0&&o!==a.retryLane&&(a.retryLane=o,yr(e,o),En(r,e,o,-1))}return Kp(),r=ff(Error(H(421))),$s(e,t,l,r)}return o.data==="$?"?(t.flags|=128,t.child=e.child,t=vR.bind(null,e),o._reactRetry=t,null):(e=a.treeContext,Ut=Xr(o.nextSibling),Kt=t,De=!0,Tn=null,e!==null&&(sn[cn++]=vr,sn[cn++]=gr,sn[cn++]=Vo,vr=e.id,gr=e.overflow,Vo=t),t=Wp(t,r.children),t.flags|=4096,t)}function vb(e,t,n){e.lanes|=t;var r=e.alternate;r!==null&&(r.lanes|=t),Uf(e.return,t,n)}function pf(e,t,n,r,o){var a=e.memoizedState;a===null?e.memoizedState={isBackwards:t,rendering:null,renderingStartTime:0,last:r,tail:n,tailMode:o}:(a.isBackwards=t,a.rendering=null,a.renderingStartTime=0,a.last=r,a.tail=n,a.tailMode=o)}function ry(e,t,n){var r=t.pendingProps,o=r.revealOrder,a=r.tail;if(Pt(e,t,r.children,n),r=Ke.current,(r&2)!==0)r=r&1|2,t.flags|=128;else{if(e!==null&&(e.flags&128)!==0)e:for(e=t.child;e!==null;){if(e.tag===13)e.memoizedState!==null&&vb(e,n,t);else if(e.tag===19)vb(e,n,t);else if(e.child!==null){e.child.return=e,e=e.child;continue}if(e===t)break e;for(;e.sibling===null;){if(e.return===null||e.return===t)break e;e=e.return}e.sibling.return=e.return,e=e.sibling}r&=1}if(Be(Ke,r),(t.mode&1)===0)t.memoizedState=null;else switch(o){case"forwards":for(n=t.child,o=null;n!==null;)e=n.alternate,e!==null&&xc(e)===null&&(o=n),n=n.sibling;n=o,n===null?(o=t.child,t.child=null):(o=n.sibling,n.sibling=null),pf(t,!1,o,n,a);break;case"backwards":for(n=null,o=t.child,t.child=null;o!==null;){if(e=o.alternate,e!==null&&xc(e)===null){t.child=o;break}e=o.sibling,o.sibling=n,n=o,o=e}pf(t,!0,n,null,a);break;case"together":pf(t,!1,null,null,void 0);break;default:t.memoizedState=null}return t.child}function Js(e,t){(t.mode&1)===0&&e!==null&&(e.alternate=null,t.alternate=null,t.flags|=2)}function wr(e,t,n){if(e!==null&&(t.dependencies=e.dependencies),$o|=t.lanes,(n&t.childLanes)===0)return null;if(e!==null&&t.child!==e.child)throw Error(H(153));if(t.child!==null){for(e=t.child,n=to(e,e.pendingProps),t.child=n,n.return=t;e.sibling!==null;)e=e.sibling,n=n.sibling=to(e,e.pendingProps),n.return=t;n.sibling=null}return t.child}function rR(e,t,n){switch(t.tag){case 3:ty(t),Ma();break;case 5:Px(t);break;case 1:Wt(t.type)&&pc(t);break;case 4:Op(t,t.stateNode.containerInfo);break;case 10:var r=t.type._context,o=t.memoizedProps.value;Be(gc,r._currentValue),r._currentValue=o;break;case 13:if(r=t.memoizedState,r!==null)return r.dehydrated!==null?(Be(Ke,Ke.current&1),t.flags|=128,null):(n&t.child.childLanes)!==0?ny(e,t,n):(Be(Ke,Ke.current&1),e=wr(e,t,n),e!==null?e.sibling:null);Be(Ke,Ke.current&1);break;case 19:if(r=(n&t.childLanes)!==0,(e.flags&128)!==0){if(r)return ry(e,t,n);t.flags|=128}if(o=t.memoizedState,o!==null&&(o.rendering=null,o.tail=null,o.lastEffect=null),Be(Ke,Ke.current),r)break;return null;case 22:case 23:return t.lanes=0,Jx(e,t,n)}return wr(e,t,n)}var oy,Jf,ay,ly;oy=function(e,t){for(var n=t.child;n!==null;){if(n.tag===5||n.tag===6)e.appendChild(n.stateNode);else if(n.tag!==4&&n.child!==null){n.child.return=n,n=n.child;continue}if(n===t)break;for(;n.sibling===null;){if(n.return===null||n.return===t)return;n=n.return}n.sibling.return=n.return,n=n.sibling}};Jf=function(){};ay=function(e,t,n,r){var o=e.memoizedProps;if(o!==r){e=t.stateNode,Do(Qn.current);var a=null;switch(n){case"input":o=wf(e,o),r=wf(e,r),a=[];break;case"select":o=qe({},o,{value:void 0}),r=qe({},r,{value:void 0}),a=[];break;case"textarea":o=Sf(e,o),r=Sf(e,r),a=[];break;default:typeof o.onClick!="function"&&typeof r.onClick=="function"&&(e.onclick=dc)}Tf(n,r);var l;n=null;for(c in o)if(!r.hasOwnProperty(c)&&o.hasOwnProperty(c)&&o[c]!=null)if(c==="style"){var i=o[c];for(l in i)i.hasOwnProperty(l)&&(n||(n={}),n[l]="")}else c!=="dangerouslySetInnerHTML"&&c!=="children"&&c!=="suppressContentEditableWarning"&&c!=="suppressHydrationWarning"&&c!=="autoFocus"&&(ei.hasOwnProperty(c)?a||(a=[]):(a=a||[]).push(c,null));for(c in r){var s=r[c];if(i=o?.[c],r.hasOwnProperty(c)&&s!==i&&(s!=null||i!=null))if(c==="style")if(i){for(l in i)!i.hasOwnProperty(l)||s&&s.hasOwnProperty(l)||(n||(n={}),n[l]="");for(l in s)s.hasOwnProperty(l)&&i[l]!==s[l]&&(n||(n={}),n[l]=s[l])}else n||(a||(a=[]),a.push(c,n)),n=s;else c==="dangerouslySetInnerHTML"?(s=s?s.__html:void 0,i=i?i.__html:void 0,s!=null&&i!==s&&(a=a||[]).push(c,s)):c==="children"?typeof s!="string"&&typeof s!="number"||(a=a||[]).push(c,""+s):c!=="suppressContentEditableWarning"&&c!=="suppressHydrationWarning"&&(ei.hasOwnProperty(c)?(s!=null&&c==="onScroll"&&Ae("scroll",e),a||i===s||(a=[])):(a=a||[]).push(c,s))}n&&(a=a||[]).push("style",n);var c=a;(t.updateQueue=c)&&(t.flags|=4)}};ly=function(e,t,n,r){n!==r&&(t.flags|=4)};function Dl(e,t){if(!De)switch(e.tailMode){case"hidden":t=e.tail;for(var n=null;t!==null;)t.alternate!==null&&(n=t),t=t.sibling;n===null?e.tail=null:n.sibling=null;break;case"collapsed":n=e.tail;for(var r=null;n!==null;)n.alternate!==null&&(r=n),n=n.sibling;r===null?t||e.tail===null?e.tail=null:e.tail.sibling=null:r.sibling=null}}function xt(e){var t=e.alternate!==null&&e.alternate.child===e.child,n=0,r=0;if(t)for(var o=e.child;o!==null;)n|=o.lanes|o.childLanes,r|=o.subtreeFlags&14680064,r|=o.flags&14680064,o.return=e,o=o.sibling;else for(o=e.child;o!==null;)n|=o.lanes|o.childLanes,r|=o.subtreeFlags,r|=o.flags,o.return=e,o=o.sibling;return e.subtreeFlags|=r,e.childLanes=n,t}function oR(e,t,n){var r=t.pendingProps;switch(kp(t),t.tag){case 2:case 16:case 15:case 0:case 11:case 7:case 8:case 12:case 9:case 14:return xt(t),null;case 1:return Wt(t.type)&&fc(),xt(t),null;case 3:return r=t.stateNode,za(),Fe(zt),Fe(wt),Bp(),r.pendingContext&&(r.context=r.pendingContext,r.pendingContext=null),(e===null||e.child===null)&&(Vs(t)?t.flags|=4:e===null||e.memoizedState.isDehydrated&&(t.flags&256)===0||(t.flags|=1024,Tn!==null&&(ip(Tn),Tn=null))),Jf(e,t),xt(t),null;case 5:Np(t);var o=Do(fi.current);if(n=t.type,e!==null&&t.stateNode!=null)ay(e,t,n,r,o),e.ref!==t.ref&&(t.flags|=512,t.flags|=2097152);else{if(!r){if(t.stateNode===null)throw Error(H(166));return xt(t),null}if(e=Do(Qn.current),Vs(t)){r=t.stateNode,n=t.type;var a=t.memoizedProps;switch(r[qn]=t,r[ui]=a,e=(t.mode&1)!==0,n){case"dialog":Ae("cancel",r),Ae("close",r);break;case"iframe":case"object":case"embed":Ae("load",r);break;case"video":case"audio":for(o=0;o<$l.length;o++)Ae($l[o],r);break;case"source":Ae("error",r);break;case"img":case"image":case"link":Ae("error",r),Ae("load",r);break;case"details":Ae("toggle",r);break;case"input":Ch(r,a),Ae("invalid",r);break;case"select":r._wrapperState={wasMultiple:!!a.multiple},Ae("invalid",r);break;case"textarea":kh(r,a),Ae("invalid",r)}Tf(n,a),o=null;for(var l in a)if(a.hasOwnProperty(l)){var i=a[l];l==="children"?typeof i=="string"?r.textContent!==i&&(a.suppressHydrationWarning!==!0&&js(r.textContent,i,e),o=["children",i]):typeof i=="number"&&r.textContent!==""+i&&(a.suppressHydrationWarning!==!0&&js(r.textContent,i,e),o=["children",""+i]):ei.hasOwnProperty(l)&&i!=null&&l==="onScroll"&&Ae("scroll",r)}switch(n){case"input":Ps(r),Sh(r,a,!0);break;case"textarea":Ps(r),Th(r);break;case"select":case"option":break;default:typeof a.onClick=="function"&&(r.onclick=dc)}r=o,t.updateQueue=r,r!==null&&(t.flags|=4)}else{l=o.nodeType===9?o:o.ownerDocument,e==="http://www.w3.org/1999/xhtml"&&(e=Bb(n)),e==="http://www.w3.org/1999/xhtml"?n==="script"?(e=l.createElement("div"),e.innerHTML="<script><\/script>",e=e.removeChild(e.firstChild)):typeof r.is=="string"?e=l.createElement(n,{is:r.is}):(e=l.createElement(n),n==="select"&&(l=e,r.multiple?l.multiple=!0:r.size&&(l.size=r.size))):e=l.createElementNS(e,n),e[qn]=t,e[ui]=r,oy(e,t,!1,!1),t.stateNode=e;e:{switch(l=Rf(n,r),n){case"dialog":Ae("cancel",e),Ae("close",e),o=r;break;case"iframe":case"object":case"embed":Ae("load",e),o=r;break;case"video":case"audio":for(o=0;o<$l.length;o++)Ae($l[o],e);o=r;break;case"source":Ae("error",e),o=r;break;case"img":case"image":case"link":Ae("error",e),Ae("load",e),o=r;break;case"details":Ae("toggle",e),o=r;break;case"input":Ch(e,r),o=wf(e,r),Ae("invalid",e);break;case"option":o=r;break;case"select":e._wrapperState={wasMultiple:!!r.multiple},o=qe({},r,{value:void 0}),Ae("invalid",e);break;case"textarea":kh(e,r),o=Sf(e,r),Ae("invalid",e);break;default:o=r}Tf(n,o),i=o;for(a in i)if(i.hasOwnProperty(a)){var s=i[a];a==="style"?Mb(e,s):a==="dangerouslySetInnerHTML"?(s=s?s.__html:void 0,s!=null&&Ab(e,s)):a==="children"?typeof s=="string"?(n!=="textarea"||s!=="")&&ti(e,s):typeof s=="number"&&ti(e,""+s):a!=="suppressContentEditableWarning"&&a!=="suppressHydrationWarning"&&a!=="autoFocus"&&(ei.hasOwnProperty(a)?s!=null&&a==="onScroll"&&Ae("scroll",e):s!=null&&up(e,a,s,l))}switch(n){case"input":Ps(e),Sh(e,r,!1);break;case"textarea":Ps(e),Th(e);break;case"option":r.value!=null&&e.setAttribute("value",""+no(r.value));break;case"select":e.multiple=!!r.multiple,a=r.value,a!=null?Pa(e,!!r.multiple,a,!1):r.defaultValue!=null&&Pa(e,!!r.multiple,r.defaultValue,!0);break;default:typeof o.onClick=="function"&&(e.onclick=dc)}switch(n){case"button":case"input":case"select":case"textarea":r=!!r.autoFocus;break e;case"img":r=!0;break e;default:r=!1}}r&&(t.flags|=4)}t.ref!==null&&(t.flags|=512,t.flags|=2097152)}return xt(t),null;case 6:if(e&&t.stateNode!=null)ly(e,t,e.memoizedProps,r);else{if(typeof r!="string"&&t.stateNode===null)throw Error(H(166));if(n=Do(fi.current),Do(Qn.current),Vs(t)){if(r=t.stateNode,n=t.memoizedProps,r[qn]=t,(a=r.nodeValue!==n)&&(e=Kt,e!==null))switch(e.tag){case 3:js(r.nodeValue,n,(e.mode&1)!==0);break;case 5:e.memoizedProps.suppressHydrationWarning!==!0&&js(r.nodeValue,n,(e.mode&1)!==0)}a&&(t.flags|=4)}else r=(n.nodeType===9?n:n.ownerDocument).createTextNode(r),r[qn]=t,t.stateNode=r}return xt(t),null;case 13:if(Fe(Ke),r=t.memoizedState,e===null||e.memoizedState!==null&&e.memoizedState.dehydrated!==null){if(De&&Ut!==null&&(t.mode&1)!==0&&(t.flags&128)===0)Sx(),Ma(),t.flags|=98560,a=!1;else if(a=Vs(t),r!==null&&r.dehydrated!==null){if(e===null){if(!a)throw Error(H(318));if(a=t.memoizedState,a=a!==null?a.dehydrated:null,!a)throw Error(H(317));a[qn]=t}else Ma(),(t.flags&128)===0&&(t.memoizedState=null),t.flags|=4;xt(t),a=!1}else Tn!==null&&(ip(Tn),Tn=null),a=!0;if(!a)return t.flags&65536?t:null}return(t.flags&128)!==0?(t.lanes=n,t):(r=r!==null,r!==(e!==null&&e.memoizedState!==null)&&r&&(t.child.flags|=8192,(t.mode&1)!==0&&(e===null||(Ke.current&1)!==0?lt===0&&(lt=3):Kp())),t.updateQueue!==null&&(t.flags|=4),xt(t),null);case 4:return za(),Jf(e,t),e===null&&si(t.stateNode.containerInfo),xt(t),null;case 10:return Pp(t.type._context),xt(t),null;case 17:return Wt(t.type)&&fc(),xt(t),null;case 19:if(Fe(Ke),a=t.memoizedState,a===null)return xt(t),null;if(r=(t.flags&128)!==0,l=a.rendering,l===null)if(r)Dl(a,!1);else{if(lt!==0||e!==null&&(e.flags&128)!==0)for(e=t.child;e!==null;){if(l=xc(e),l!==null){for(t.flags|=128,Dl(a,!1),r=l.updateQueue,r!==null&&(t.updateQueue=r,t.flags|=4),t.subtreeFlags=0,r=n,n=t.child;n!==null;)a=n,e=r,a.flags&=14680066,l=a.alternate,l===null?(a.childLanes=0,a.lanes=e,a.child=null,a.subtreeFlags=0,a.memoizedProps=null,a.memoizedState=null,a.updateQueue=null,a.dependencies=null,a.stateNode=null):(a.childLanes=l.childLanes,a.lanes=l.lanes,a.child=l.child,a.subtreeFlags=0,a.deletions=null,a.memoizedProps=l.memoizedProps,a.memoizedState=l.memoizedState,a.updateQueue=l.updateQueue,a.type=l.type,e=l.dependencies,a.dependencies=e===null?null:{lanes:e.lanes,firstContext:e.firstContext}),n=n.sibling;return Be(Ke,Ke.current&1|2),t.child}e=e.sibling}a.tail!==null&&Xe()>ja&&(t.flags|=128,r=!0,Dl(a,!1),t.lanes=4194304)}else{if(!r)if(e=xc(l),e!==null){if(t.flags|=128,r=!0,n=e.updateQueue,n!==null&&(t.updateQueue=n,t.flags|=4),Dl(a,!0),a.tail===null&&a.tailMode==="hidden"&&!l.alternate&&!De)return xt(t),null}else 2*Xe()-a.renderingStartTime>ja&&n!==1073741824&&(t.flags|=128,r=!0,Dl(a,!1),t.lanes=4194304);a.isBackwards?(l.sibling=t.child,t.child=l):(n=a.last,n!==null?n.sibling=l:t.child=l,a.last=l)}return a.tail!==null?(t=a.tail,a.rendering=t,a.tail=t.sibling,a.renderingStartTime=Xe(),t.sibling=null,n=Ke.current,Be(Ke,r?n&1|2:n&1),t):(xt(t),null);case 22:case 23:return Up(),r=t.memoizedState!==null,e!==null&&e.memoizedState!==null!==r&&(t.flags|=8192),r&&(t.mode&1)!==0?($t&1073741824)!==0&&(xt(t),t.subtreeFlags&6&&(t.flags|=8192)):xt(t),null;case 24:return null;case 25:return null}throw Error(H(156,t.tag))}function aR(e,t){switch(kp(t),t.tag){case 1:return Wt(t.type)&&fc(),e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 3:return za(),Fe(zt),Fe(wt),Bp(),e=t.flags,(e&65536)!==0&&(e&128)===0?(t.flags=e&-65537|128,t):null;case 5:return Np(t),null;case 13:if(Fe(Ke),e=t.memoizedState,e!==null&&e.dehydrated!==null){if(t.alternate===null)throw Error(H(340));Ma()}return e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 19:return Fe(Ke),null;case 4:return za(),null;case 10:return Pp(t.type._context),null;case 22:case 23:return Up(),null;case 24:return null;default:return null}}var Us=!1,yt=!1,lR=typeof WeakSet=="function"?WeakSet:Set,ae=null;function Ra(e,t){var n=e.ref;if(n!==null)if(typeof n=="function")try{n(null)}catch(r){Ye(e,t,r)}else n.current=null}function ep(e,t,n){try{n()}catch(r){Ye(e,t,r)}}var gb=!1;function iR(e,t){if(Mf=sc,e=dx(),Cp(e)){if("selectionStart"in e)var n={start:e.selectionStart,end:e.selectionEnd};else e:{n=(n=e.ownerDocument)&&n.defaultView||window;var r=n.getSelection&&n.getSelection();if(r&&r.rangeCount!==0){n=r.anchorNode;var o=r.anchorOffset,a=r.focusNode;r=r.focusOffset;try{n.nodeType,a.nodeType}catch{n=null;break e}var l=0,i=-1,s=-1,c=0,d=0,p=e,g=null;t:for(;;){for(var m;p!==n||o!==0&&p.nodeType!==3||(i=l+o),p!==a||r!==0&&p.nodeType!==3||(s=l+r),p.nodeType===3&&(l+=p.nodeValue.length),(m=p.firstChild)!==null;)g=p,p=m;for(;;){if(p===e)break t;if(g===n&&++c===o&&(i=l),g===a&&++d===r&&(s=l),(m=p.nextSibling)!==null)break;p=g,g=p.parentNode}p=m}n=i===-1||s===-1?null:{start:i,end:s}}else n=null}n=n||{start:0,end:0}}else n=null;for(Df={focusedElem:e,selectionRange:n},sc=!1,ae=t;ae!==null;)if(t=ae,e=t.child,(t.subtreeFlags&1028)!==0&&e!==null)e.return=t,ae=e;else for(;ae!==null;){t=ae;try{var b=t.alternate;if((t.flags&1024)!==0)switch(t.tag){case 0:case 11:case 15:break;case 1:if(b!==null){var h=b.memoizedProps,y=b.memoizedState,v=t.stateNode,u=v.getSnapshotBeforeUpdate(t.elementType===t.type?h:Sn(t.type,h),y);v.__reactInternalSnapshotBeforeUpdate=u}break;case 3:var f=t.stateNode.containerInfo;f.nodeType===1?f.textContent="":f.nodeType===9&&f.documentElement&&f.removeChild(f.documentElement);break;case 5:case 6:case 4:case 17:break;default:throw Error(H(163))}}catch(x){Ye(t,t.return,x)}if(e=t.sibling,e!==null){e.return=t.return,ae=e;break}ae=t.return}return b=gb,gb=!1,b}function Xl(e,t,n){var r=t.updateQueue;if(r=r!==null?r.lastEffect:null,r!==null){var o=r=r.next;do{if((o.tag&e)===e){var a=o.destroy;o.destroy=void 0,a!==void 0&&ep(t,n,a)}o=o.next}while(o!==r)}}function Ac(e,t){if(t=t.updateQueue,t=t!==null?t.lastEffect:null,t!==null){var n=t=t.next;do{if((n.tag&e)===e){var r=n.create;n.destroy=r()}n=n.next}while(n!==t)}}function tp(e){var t=e.ref;if(t!==null){var n=e.stateNode;switch(e.tag){case 5:e=n;break;default:e=n}typeof t=="function"?t(e):t.current=e}}function iy(e){var t=e.alternate;t!==null&&(e.alternate=null,iy(t)),e.child=null,e.deletions=null,e.sibling=null,e.tag===5&&(t=e.stateNode,t!==null&&(delete t[qn],delete t[ui],delete t[jf],delete t[HT],delete t[$T])),e.stateNode=null,e.return=null,e.dependencies=null,e.memoizedProps=null,e.memoizedState=null,e.pendingProps=null,e.stateNode=null,e.updateQueue=null}function sy(e){return e.tag===5||e.tag===3||e.tag===4}function hb(e){e:for(;;){for(;e.sibling===null;){if(e.return===null||sy(e.return))return null;e=e.return}for(e.sibling.return=e.return,e=e.sibling;e.tag!==5&&e.tag!==6&&e.tag!==18;){if(e.flags&2||e.child===null||e.tag===4)continue e;e.child.return=e,e=e.child}if(!(e.flags&2))return e.stateNode}}function np(e,t,n){var r=e.tag;if(r===5||r===6)e=e.stateNode,t?n.nodeType===8?n.parentNode.insertBefore(e,t):n.insertBefore(e,t):(n.nodeType===8?(t=n.parentNode,t.insertBefore(e,n)):(t=n,t.appendChild(e)),n=n._reactRootContainer,n!=null||t.onclick!==null||(t.onclick=dc));else if(r!==4&&(e=e.child,e!==null))for(np(e,t,n),e=e.sibling;e!==null;)np(e,t,n),e=e.sibling}function rp(e,t,n){var r=e.tag;if(r===5||r===6)e=e.stateNode,t?n.insertBefore(e,t):n.appendChild(e);else if(r!==4&&(e=e.child,e!==null))for(rp(e,t,n),e=e.sibling;e!==null;)rp(e,t,n),e=e.sibling}var dt=null,kn=!1;function jr(e,t,n){for(n=n.child;n!==null;)cy(e,t,n),n=n.sibling}function cy(e,t,n){if(Yn&&typeof Yn.onCommitFiberUnmount=="function")try{Yn.onCommitFiberUnmount(Rc,n)}catch{}switch(n.tag){case 5:yt||Ra(n,t);case 6:var r=dt,o=kn;dt=null,jr(e,t,n),dt=r,kn=o,dt!==null&&(kn?(e=dt,n=n.stateNode,e.nodeType===8?e.parentNode.removeChild(n):e.removeChild(n)):dt.removeChild(n.stateNode));break;case 18:dt!==null&&(kn?(e=dt,n=n.stateNode,e.nodeType===8?af(e.parentNode,n):e.nodeType===1&&af(e,n),ai(e)):af(dt,n.stateNode));break;case 4:r=dt,o=kn,dt=n.stateNode.containerInfo,kn=!0,jr(e,t,n),dt=r,kn=o;break;case 0:case 11:case 14:case 15:if(!yt&&(r=n.updateQueue,r!==null&&(r=r.lastEffect,r!==null))){o=r=r.next;do{var a=o,l=a.destroy;a=a.tag,l!==void 0&&((a&2)!==0||(a&4)!==0)&&ep(n,t,l),o=o.next}while(o!==r)}jr(e,t,n);break;case 1:if(!yt&&(Ra(n,t),r=n.stateNode,typeof r.componentWillUnmount=="function"))try{r.props=n.memoizedProps,r.state=n.memoizedState,r.componentWillUnmount()}catch(i){Ye(n,t,i)}jr(e,t,n);break;case 21:jr(e,t,n);break;case 22:n.mode&1?(yt=(r=yt)||n.memoizedState!==null,jr(e,t,n),yt=r):jr(e,t,n);break;default:jr(e,t,n)}}function bb(e){var t=e.updateQueue;if(t!==null){e.updateQueue=null;var n=e.stateNode;n===null&&(n=e.stateNode=new lR),t.forEach(function(r){var o=gR.bind(null,e,r);n.has(r)||(n.add(r),r.then(o,o))})}}function Cn(e,t){var n=t.deletions;if(n!==null)for(var r=0;r<n.length;r++){var o=n[r];try{var a=e,l=t,i=l;e:for(;i!==null;){switch(i.tag){case 5:dt=i.stateNode,kn=!1;break e;case 3:dt=i.stateNode.containerInfo,kn=!0;break e;case 4:dt=i.stateNode.containerInfo,kn=!0;break e}i=i.return}if(dt===null)throw Error(H(160));cy(a,l,o),dt=null,kn=!1;var s=o.alternate;s!==null&&(s.return=null),o.return=null}catch(c){Ye(o,t,c)}}if(t.subtreeFlags&12854)for(t=t.child;t!==null;)uy(t,e),t=t.sibling}function uy(e,t){var n=e.alternate,r=e.flags;switch(e.tag){case 0:case 11:case 14:case 15:if(Cn(t,e),Kn(e),r&4){try{Xl(3,e,e.return),Ac(3,e)}catch(h){Ye(e,e.return,h)}try{Xl(5,e,e.return)}catch(h){Ye(e,e.return,h)}}break;case 1:Cn(t,e),Kn(e),r&512&&n!==null&&Ra(n,n.return);break;case 5:if(Cn(t,e),Kn(e),r&512&&n!==null&&Ra(n,n.return),e.flags&32){var o=e.stateNode;try{ti(o,"")}catch(h){Ye(e,e.return,h)}}if(r&4&&(o=e.stateNode,o!=null)){var a=e.memoizedProps,l=n!==null?n.memoizedProps:a,i=e.type,s=e.updateQueue;if(e.updateQueue=null,s!==null)try{i==="input"&&a.type==="radio"&&a.name!=null&&Ob(o,a),Rf(i,l);var c=Rf(i,a);for(l=0;l<s.length;l+=2){var d=s[l],p=s[l+1];d==="style"?Mb(o,p):d==="dangerouslySetInnerHTML"?Ab(o,p):d==="children"?ti(o,p):up(o,d,p,c)}switch(i){case"input":If(o,a);break;case"textarea":Nb(o,a);break;case"select":var g=o._wrapperState.wasMultiple;o._wrapperState.wasMultiple=!!a.multiple;var m=a.value;m!=null?Pa(o,!!a.multiple,m,!1):g!==!!a.multiple&&(a.defaultValue!=null?Pa(o,!!a.multiple,a.defaultValue,!0):Pa(o,!!a.multiple,a.multiple?[]:"",!1))}o[ui]=a}catch(h){Ye(e,e.return,h)}}break;case 6:if(Cn(t,e),Kn(e),r&4){if(e.stateNode===null)throw Error(H(162));o=e.stateNode,a=e.memoizedProps;try{o.nodeValue=a}catch(h){Ye(e,e.return,h)}}break;case 3:if(Cn(t,e),Kn(e),r&4&&n!==null&&n.memoizedState.isDehydrated)try{ai(t.containerInfo)}catch(h){Ye(e,e.return,h)}break;case 4:Cn(t,e),Kn(e);break;case 13:Cn(t,e),Kn(e),o=e.child,o.flags&8192&&(a=o.memoizedState!==null,o.stateNode.isHidden=a,!a||o.alternate!==null&&o.alternate.memoizedState!==null||(Hp=Xe())),r&4&&bb(e);break;case 22:if(d=n!==null&&n.memoizedState!==null,e.mode&1?(yt=(c=yt)||d,Cn(t,e),yt=c):Cn(t,e),Kn(e),r&8192){if(c=e.memoizedState!==null,(e.stateNode.isHidden=c)&&!d&&(e.mode&1)!==0)for(ae=e,d=e.child;d!==null;){for(p=ae=d;ae!==null;){switch(g=ae,m=g.child,g.tag){case 0:case 11:case 14:case 15:Xl(4,g,g.return);break;case 1:Ra(g,g.return);var b=g.stateNode;if(typeof b.componentWillUnmount=="function"){r=g,n=g.return;try{t=r,b.props=t.memoizedProps,b.state=t.memoizedState,b.componentWillUnmount()}catch(h){Ye(r,n,h)}}break;case 5:Ra(g,g.return);break;case 22:if(g.memoizedState!==null){yb(p);continue}}m!==null?(m.return=g,ae=m):yb(p)}d=d.sibling}e:for(d=null,p=e;;){if(p.tag===5){if(d===null){d=p;try{o=p.stateNode,c?(a=o.style,typeof a.setProperty=="function"?a.setProperty("display","none","important"):a.display="none"):(i=p.stateNode,s=p.memoizedProps.style,l=s!=null&&s.hasOwnProperty("display")?s.display:null,i.style.display=Fb("display",l))}catch(h){Ye(e,e.return,h)}}}else if(p.tag===6){if(d===null)try{p.stateNode.nodeValue=c?"":p.memoizedProps}catch(h){Ye(e,e.return,h)}}else if((p.tag!==22&&p.tag!==23||p.memoizedState===null||p===e)&&p.child!==null){p.child.return=p,p=p.child;continue}if(p===e)break e;for(;p.sibling===null;){if(p.return===null||p.return===e)break e;d===p&&(d=null),p=p.return}d===p&&(d=null),p.sibling.return=p.return,p=p.sibling}}break;case 19:Cn(t,e),Kn(e),r&4&&bb(e);break;case 21:break;default:Cn(t,e),Kn(e)}}function Kn(e){var t=e.flags;if(t&2){try{e:{for(var n=e.return;n!==null;){if(sy(n)){var r=n;break e}n=n.return}throw Error(H(160))}switch(r.tag){case 5:var o=r.stateNode;r.flags&32&&(ti(o,""),r.flags&=-33);var a=hb(e);rp(e,a,o);break;case 3:case 4:var l=r.stateNode.containerInfo,i=hb(e);np(e,i,l);break;default:throw Error(H(161))}}catch(s){Ye(e,e.return,s)}e.flags&=-3}t&4096&&(e.flags&=-4097)}function sR(e,t,n){ae=e,dy(e,t,n)}function dy(e,t,n){for(var r=(e.mode&1)!==0;ae!==null;){var o=ae,a=o.child;if(o.tag===22&&r){var l=o.memoizedState!==null||Us;if(!l){var i=o.alternate,s=i!==null&&i.memoizedState!==null||yt;i=Us;var c=yt;if(Us=l,(yt=s)&&!c)for(ae=o;ae!==null;)l=ae,s=l.child,l.tag===22&&l.memoizedState!==null?wb(o):s!==null?(s.return=l,ae=s):wb(o);for(;a!==null;)ae=a,dy(a,t,n),a=a.sibling;ae=o,Us=i,yt=c}xb(e,t,n)}else(o.subtreeFlags&8772)!==0&&a!==null?(a.return=o,ae=a):xb(e,t,n)}}function xb(e){for(;ae!==null;){var t=ae;if((t.flags&8772)!==0){var n=t.alternate;try{if((t.flags&8772)!==0)switch(t.tag){case 0:case 11:case 15:yt||Ac(5,t);break;case 1:var r=t.stateNode;if(t.flags&4&&!yt)if(n===null)r.componentDidMount();else{var o=t.elementType===t.type?n.memoizedProps:Sn(t.type,n.memoizedProps);r.componentDidUpdate(o,n.memoizedState,r.__reactInternalSnapshotBeforeUpdate)}var a=t.updateQueue;a!==null&&rb(t,a,r);break;case 3:var l=t.updateQueue;if(l!==null){if(n=null,t.child!==null)switch(t.child.tag){case 5:n=t.child.stateNode;break;case 1:n=t.child.stateNode}rb(t,l,n)}break;case 5:var i=t.stateNode;if(n===null&&t.flags&4){n=i;var s=t.memoizedProps;switch(t.type){case"button":case"input":case"select":case"textarea":s.autoFocus&&n.focus();break;case"img":s.src&&(n.src=s.src)}}break;case 6:break;case 4:break;case 12:break;case 13:if(t.memoizedState===null){var c=t.alternate;if(c!==null){var d=c.memoizedState;if(d!==null){var p=d.dehydrated;p!==null&&ai(p)}}}break;case 19:case 17:case 21:case 22:case 23:case 25:break;default:throw Error(H(163))}yt||t.flags&512&&tp(t)}catch(g){Ye(t,t.return,g)}}if(t===e){ae=null;break}if(n=t.sibling,n!==null){n.return=t.return,ae=n;break}ae=t.return}}function yb(e){for(;ae!==null;){var t=ae;if(t===e){ae=null;break}var n=t.sibling;if(n!==null){n.return=t.return,ae=n;break}ae=t.return}}function wb(e){for(;ae!==null;){var t=ae;try{switch(t.tag){case 0:case 11:case 15:var n=t.return;try{Ac(4,t)}catch(s){Ye(t,n,s)}break;case 1:var r=t.stateNode;if(typeof r.componentDidMount=="function"){var o=t.return;try{r.componentDidMount()}catch(s){Ye(t,o,s)}}var a=t.return;try{tp(t)}catch(s){Ye(t,a,s)}break;case 5:var l=t.return;try{tp(t)}catch(s){Ye(t,l,s)}}}catch(s){Ye(t,t.return,s)}if(t===e){ae=null;break}var i=t.sibling;if(i!==null){i.return=t.return,ae=i;break}ae=t.return}}var cR=Math.ceil,Ic=Ir.ReactCurrentDispatcher,jp=Ir.ReactCurrentOwner,dn=Ir.ReactCurrentBatchConfig,Te=0,ct=null,et=null,ft=0,$t=0,Ea=ao(0),lt=0,gi=null,$o=0,Fc=0,Vp=0,Zl=null,Mt=null,Hp=0,ja=1/0,pr=null,Cc=!1,op=null,Jr=null,Ks=!1,Gr=null,Sc=0,Jl=0,ap=null,ec=-1,tc=0;function _t(){return(Te&6)!==0?Xe():ec!==-1?ec:ec=Xe()}function eo(e){return(e.mode&1)===0?1:(Te&2)!==0&&ft!==0?ft&-ft:KT.transition!==null?(tc===0&&(tc=Yb()),tc):(e=Pe,e!==0||(e=window.event,e=e===void 0?16:nx(e.type)),e)}function En(e,t,n,r){if(50<Jl)throw Jl=0,ap=null,Error(H(185));hi(e,n,r),((Te&2)===0||e!==ct)&&(e===ct&&((Te&2)===0&&(Fc|=n),lt===4&&Ur(e,ft)),jt(e,r),n===1&&Te===0&&(t.mode&1)===0&&(ja=Xe()+500,Oc&&lo()))}function jt(e,t){var n=e.callbackNode;qk(e,t);var r=ic(e,e===ct?ft:0);if(r===0)n!==null&&Ph(n),e.callbackNode=null,e.callbackPriority=0;else if(t=r&-r,e.callbackPriority!==t){if(n!=null&&Ph(n),t===1)e.tag===0?UT(Ib.bind(null,e)):wx(Ib.bind(null,e)),jT(function(){(Te&6)===0&&lo()}),n=null;else{switch(Qb(r)){case 1:n=vp;break;case 4:n=Gb;break;case 16:n=lc;break;case 536870912:n=qb;break;default:n=lc}n=xy(n,fy.bind(null,e))}e.callbackPriority=t,e.callbackNode=n}}function fy(e,t){if(ec=-1,tc=0,(Te&6)!==0)throw Error(H(327));var n=e.callbackNode;if(Ba()&&e.callbackNode!==n)return null;var r=ic(e,e===ct?ft:0);if(r===0)return null;if((r&30)!==0||(r&e.expiredLanes)!==0||t)t=kc(e,r);else{t=r;var o=Te;Te|=2;var a=my();(ct!==e||ft!==t)&&(pr=null,ja=Xe()+500,zo(e,t));do try{fR();break}catch(i){py(e,i)}while(!0);Ep(),Ic.current=a,Te=o,et!==null?t=0:(ct=null,ft=0,t=lt)}if(t!==0){if(t===2&&(o=Of(e),o!==0&&(r=o,t=lp(e,o))),t===1)throw n=gi,zo(e,0),Ur(e,r),jt(e,Xe()),n;if(t===6)Ur(e,r);else{if(o=e.current.alternate,(r&30)===0&&!uR(o)&&(t=kc(e,r),t===2&&(a=Of(e),a!==0&&(r=a,t=lp(e,a))),t===1))throw n=gi,zo(e,0),Ur(e,r),jt(e,Xe()),n;switch(e.finishedWork=o,e.finishedLanes=r,t){case 0:case 1:throw Error(H(345));case 2:Ao(e,Mt,pr);break;case 3:if(Ur(e,r),(r&130023424)===r&&(t=Hp+500-Xe(),10<t)){if(ic(e,0)!==0)break;if(o=e.suspendedLanes,(o&r)!==r){_t(),e.pingedLanes|=e.suspendedLanes&o;break}e.timeoutHandle=Wf(Ao.bind(null,e,Mt,pr),t);break}Ao(e,Mt,pr);break;case 4:if(Ur(e,r),(r&4194240)===r)break;for(t=e.eventTimes,o=-1;0<r;){var l=31-Rn(r);a=1<<l,l=t[l],l>o&&(o=l),r&=~a}if(r=o,r=Xe()-r,r=(120>r?120:480>r?480:1080>r?1080:1920>r?1920:3e3>r?3e3:4320>r?4320:1960*cR(r/1960))-r,10<r){e.timeoutHandle=Wf(Ao.bind(null,e,Mt,pr),r);break}Ao(e,Mt,pr);break;case 5:Ao(e,Mt,pr);break;default:throw Error(H(329))}}}return jt(e,Xe()),e.callbackNode===n?fy.bind(null,e):null}function lp(e,t){var n=Zl;return e.current.memoizedState.isDehydrated&&(zo(e,t).flags|=256),e=kc(e,t),e!==2&&(t=Mt,Mt=n,t!==null&&ip(t)),e}function ip(e){Mt===null?Mt=e:Mt.push.apply(Mt,e)}function uR(e){for(var t=e;;){if(t.flags&16384){var n=t.updateQueue;if(n!==null&&(n=n.stores,n!==null))for(var r=0;r<n.length;r++){var o=n[r],a=o.getSnapshot;o=o.value;try{if(!Pn(a(),o))return!1}catch{return!1}}}if(n=t.child,t.subtreeFlags&16384&&n!==null)n.return=t,t=n;else{if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return!0;t=t.return}t.sibling.return=t.return,t=t.sibling}}return!0}function Ur(e,t){for(t&=~Vp,t&=~Fc,e.suspendedLanes|=t,e.pingedLanes&=~t,e=e.expirationTimes;0<t;){var n=31-Rn(t),r=1<<n;e[n]=-1,t&=~r}}function Ib(e){if((Te&6)!==0)throw Error(H(327));Ba();var t=ic(e,0);if((t&1)===0)return jt(e,Xe()),null;var n=kc(e,t);if(e.tag!==0&&n===2){var r=Of(e);r!==0&&(t=r,n=lp(e,r))}if(n===1)throw n=gi,zo(e,0),Ur(e,t),jt(e,Xe()),n;if(n===6)throw Error(H(345));return e.finishedWork=e.current.alternate,e.finishedLanes=t,Ao(e,Mt,pr),jt(e,Xe()),null}function $p(e,t){var n=Te;Te|=1;try{return e(t)}finally{Te=n,Te===0&&(ja=Xe()+500,Oc&&lo())}}function Uo(e){Gr!==null&&Gr.tag===0&&(Te&6)===0&&Ba();var t=Te;Te|=1;var n=dn.transition,r=Pe;try{if(dn.transition=null,Pe=1,e)return e()}finally{Pe=r,dn.transition=n,Te=t,(Te&6)===0&&lo()}}function Up(){$t=Ea.current,Fe(Ea)}function zo(e,t){e.finishedWork=null,e.finishedLanes=0;var n=e.timeoutHandle;if(n!==-1&&(e.timeoutHandle=-1,WT(n)),et!==null)for(n=et.return;n!==null;){var r=n;switch(kp(r),r.tag){case 1:r=r.type.childContextTypes,r!=null&&fc();break;case 3:za(),Fe(zt),Fe(wt),Bp();break;case 5:Np(r);break;case 4:za();break;case 13:Fe(Ke);break;case 19:Fe(Ke);break;case 10:Pp(r.type._context);break;case 22:case 23:Up()}n=n.return}if(ct=e,et=e=to(e.current,null),ft=$t=t,lt=0,gi=null,Vp=Fc=$o=0,Mt=Zl=null,Mo!==null){for(t=0;t<Mo.length;t++)if(n=Mo[t],r=n.interleaved,r!==null){n.interleaved=null;var o=r.next,a=n.pending;if(a!==null){var l=a.next;a.next=o,r.next=l}n.pending=r}Mo=null}return e}function py(e,t){do{var n=et;try{if(Ep(),Xs.current=wc,yc){for(var r=Ge.memoizedState;r!==null;){var o=r.queue;o!==null&&(o.pending=null),r=r.next}yc=!1}if(Ho=0,st=at=Ge=null,Ql=!1,pi=0,jp.current=null,n===null||n.return===null){lt=1,gi=t,et=null;break}e:{var a=e,l=n.return,i=n,s=t;if(t=ft,i.flags|=32768,s!==null&&typeof s=="object"&&typeof s.then=="function"){var c=s,d=i,p=d.tag;if((d.mode&1)===0&&(p===0||p===11||p===15)){var g=d.alternate;g?(d.updateQueue=g.updateQueue,d.memoizedState=g.memoizedState,d.lanes=g.lanes):(d.updateQueue=null,d.memoizedState=null)}var m=cb(l);if(m!==null){m.flags&=-257,ub(m,l,i,a,t),m.mode&1&&sb(a,c,t),t=m,s=c;var b=t.updateQueue;if(b===null){var h=new Set;h.add(s),t.updateQueue=h}else b.add(s);break e}else{if((t&1)===0){sb(a,c,t),Kp();break e}s=Error(H(426))}}else if(De&&i.mode&1){var y=cb(l);if(y!==null){(y.flags&65536)===0&&(y.flags|=256),ub(y,l,i,a,t),Tp(Wa(s,i));break e}}a=s=Wa(s,i),lt!==4&&(lt=2),Zl===null?Zl=[a]:Zl.push(a),a=l;do{switch(a.tag){case 3:a.flags|=65536,t&=-t,a.lanes|=t;var v=Qx(a,s,t);nb(a,v);break e;case 1:i=s;var u=a.type,f=a.stateNode;if((a.flags&128)===0&&(typeof u.getDerivedStateFromError=="function"||f!==null&&typeof f.componentDidCatch=="function"&&(Jr===null||!Jr.has(f)))){a.flags|=65536,t&=-t,a.lanes|=t;var x=Xx(a,i,t);nb(a,x);break e}}a=a.return}while(a!==null)}gy(n)}catch(I){t=I,et===n&&n!==null&&(et=n=n.return);continue}break}while(!0)}function my(){var e=Ic.current;return Ic.current=wc,e===null?wc:e}function Kp(){(lt===0||lt===3||lt===2)&&(lt=4),ct===null||($o&268435455)===0&&(Fc&268435455)===0||Ur(ct,ft)}function kc(e,t){var n=Te;Te|=2;var r=my();(ct!==e||ft!==t)&&(pr=null,zo(e,t));do try{dR();break}catch(o){py(e,o)}while(!0);if(Ep(),Te=n,Ic.current=r,et!==null)throw Error(H(261));return ct=null,ft=0,lt}function dR(){for(;et!==null;)vy(et)}function fR(){for(;et!==null&&!zk();)vy(et)}function vy(e){var t=by(e.alternate,e,$t);e.memoizedProps=e.pendingProps,t===null?gy(e):et=t,jp.current=null}function gy(e){var t=e;do{var n=t.alternate;if(e=t.return,(t.flags&32768)===0){if(n=oR(n,t,$t),n!==null){et=n;return}}else{if(n=aR(n,t),n!==null){n.flags&=32767,et=n;return}if(e!==null)e.flags|=32768,e.subtreeFlags=0,e.deletions=null;else{lt=6,et=null;return}}if(t=t.sibling,t!==null){et=t;return}et=t=e}while(t!==null);lt===0&&(lt=5)}function Ao(e,t,n){var r=Pe,o=dn.transition;try{dn.transition=null,Pe=1,pR(e,t,n,r)}finally{dn.transition=o,Pe=r}return null}function pR(e,t,n,r){do Ba();while(Gr!==null);if((Te&6)!==0)throw Error(H(327));n=e.finishedWork;var o=e.finishedLanes;if(n===null)return null;if(e.finishedWork=null,e.finishedLanes=0,n===e.current)throw Error(H(177));e.callbackNode=null,e.callbackPriority=0;var a=n.lanes|n.childLanes;if(Yk(e,a),e===ct&&(et=ct=null,ft=0),(n.subtreeFlags&2064)===0&&(n.flags&2064)===0||Ks||(Ks=!0,xy(lc,function(){return Ba(),null})),a=(n.flags&15990)!==0,(n.subtreeFlags&15990)!==0||a){a=dn.transition,dn.transition=null;var l=Pe;Pe=1;var i=Te;Te|=4,jp.current=null,iR(e,n),uy(n,e),AT(Df),sc=!!Mf,Df=Mf=null,e.current=n,sR(n,e,o),Wk(),Te=i,Pe=l,dn.transition=a}else e.current=n;if(Ks&&(Ks=!1,Gr=e,Sc=o),a=e.pendingLanes,a===0&&(Jr=null),Hk(n.stateNode,r),jt(e,Xe()),t!==null)for(r=e.onRecoverableError,n=0;n<t.length;n++)o=t[n],r(o.value,{componentStack:o.stack,digest:o.digest});if(Cc)throw Cc=!1,e=op,op=null,e;return(Sc&1)!==0&&e.tag!==0&&Ba(),a=e.pendingLanes,(a&1)!==0?e===ap?Jl++:(Jl=0,ap=e):Jl=0,lo(),null}function Ba(){if(Gr!==null){var e=Qb(Sc),t=dn.transition,n=Pe;try{if(dn.transition=null,Pe=16>e?16:e,Gr===null)var r=!1;else{if(e=Gr,Gr=null,Sc=0,(Te&6)!==0)throw Error(H(331));var o=Te;for(Te|=4,ae=e.current;ae!==null;){var a=ae,l=a.child;if((ae.flags&16)!==0){var i=a.deletions;if(i!==null){for(var s=0;s<i.length;s++){var c=i[s];for(ae=c;ae!==null;){var d=ae;switch(d.tag){case 0:case 11:case 15:Xl(8,d,a)}var p=d.child;if(p!==null)p.return=d,ae=p;else for(;ae!==null;){d=ae;var g=d.sibling,m=d.return;if(iy(d),d===c){ae=null;break}if(g!==null){g.return=m,ae=g;break}ae=m}}}var b=a.alternate;if(b!==null){var h=b.child;if(h!==null){b.child=null;do{var y=h.sibling;h.sibling=null,h=y}while(h!==null)}}ae=a}}if((a.subtreeFlags&2064)!==0&&l!==null)l.return=a,ae=l;else e:for(;ae!==null;){if(a=ae,(a.flags&2048)!==0)switch(a.tag){case 0:case 11:case 15:Xl(9,a,a.return)}var v=a.sibling;if(v!==null){v.return=a.return,ae=v;break e}ae=a.return}}var u=e.current;for(ae=u;ae!==null;){l=ae;var f=l.child;if((l.subtreeFlags&2064)!==0&&f!==null)f.return=l,ae=f;else e:for(l=u;ae!==null;){if(i=ae,(i.flags&2048)!==0)try{switch(i.tag){case 0:case 11:case 15:Ac(9,i)}}catch(I){Ye(i,i.return,I)}if(i===l){ae=null;break e}var x=i.sibling;if(x!==null){x.return=i.return,ae=x;break e}ae=i.return}}if(Te=o,lo(),Yn&&typeof Yn.onPostCommitFiberRoot=="function")try{Yn.onPostCommitFiberRoot(Rc,e)}catch{}r=!0}return r}finally{Pe=n,dn.transition=t}}return!1}function Cb(e,t,n){t=Wa(n,t),t=Qx(e,t,1),e=Zr(e,t,1),t=_t(),e!==null&&(hi(e,1,t),jt(e,t))}function Ye(e,t,n){if(e.tag===3)Cb(e,e,n);else for(;t!==null;){if(t.tag===3){Cb(t,e,n);break}else if(t.tag===1){var r=t.stateNode;if(typeof t.type.getDerivedStateFromError=="function"||typeof r.componentDidCatch=="function"&&(Jr===null||!Jr.has(r))){e=Wa(n,e),e=Xx(t,e,1),t=Zr(t,e,1),e=_t(),t!==null&&(hi(t,1,e),jt(t,e));break}}t=t.return}}function mR(e,t,n){var r=e.pingCache;r!==null&&r.delete(t),t=_t(),e.pingedLanes|=e.suspendedLanes&n,ct===e&&(ft&n)===n&&(lt===4||lt===3&&(ft&130023424)===ft&&500>Xe()-Hp?zo(e,0):Vp|=n),jt(e,t)}function hy(e,t){t===0&&((e.mode&1)===0?t=1:(t=Os,Os<<=1,(Os&130023424)===0&&(Os=4194304)));var n=_t();e=yr(e,t),e!==null&&(hi(e,t,n),jt(e,n))}function vR(e){var t=e.memoizedState,n=0;t!==null&&(n=t.retryLane),hy(e,n)}function gR(e,t){var n=0;switch(e.tag){case 13:var r=e.stateNode,o=e.memoizedState;o!==null&&(n=o.retryLane);break;case 19:r=e.stateNode;break;default:throw Error(H(314))}r!==null&&r.delete(t),hy(e,n)}var by;by=function(e,t,n){if(e!==null)if(e.memoizedProps!==t.pendingProps||zt.current)Dt=!0;else{if((e.lanes&n)===0&&(t.flags&128)===0)return Dt=!1,rR(e,t,n);Dt=(e.flags&131072)!==0}else Dt=!1,De&&(t.flags&1048576)!==0&&Ix(t,vc,t.index);switch(t.lanes=0,t.tag){case 2:var r=t.type;Js(e,t),e=t.pendingProps;var o=Fa(t,wt.current);Na(t,n),o=Fp(null,t,r,e,o,n);var a=Mp();return t.flags|=1,typeof o=="object"&&o!==null&&typeof o.render=="function"&&o.$$typeof===void 0?(t.tag=1,t.memoizedState=null,t.updateQueue=null,Wt(r)?(a=!0,pc(t)):a=!1,t.memoizedState=o.state!==null&&o.state!==void 0?o.state:null,Lp(t),o.updater=Bc,t.stateNode=o,o._reactInternals=t,Gf(t,r,e,n),t=Qf(null,t,r,!0,a,n)):(t.tag=0,De&&a&&Sp(t),Pt(null,t,o,n),t=t.child),t;case 16:r=t.elementType;e:{switch(Js(e,t),e=t.pendingProps,o=r._init,r=o(r._payload),t.type=r,o=t.tag=bR(r),e=Sn(r,e),o){case 0:t=Yf(null,t,r,e,n);break e;case 1:t=pb(null,t,r,e,n);break e;case 11:t=db(null,t,r,e,n);break e;case 14:t=fb(null,t,r,Sn(r.type,e),n);break e}throw Error(H(306,r,""))}return t;case 0:return r=t.type,o=t.pendingProps,o=t.elementType===r?o:Sn(r,o),Yf(e,t,r,o,n);case 1:return r=t.type,o=t.pendingProps,o=t.elementType===r?o:Sn(r,o),pb(e,t,r,o,n);case 3:e:{if(ty(t),e===null)throw Error(H(387));r=t.pendingProps,a=t.memoizedState,o=a.element,Ex(e,t),bc(t,r,null,n);var l=t.memoizedState;if(r=l.element,a.isDehydrated)if(a={element:r,isDehydrated:!1,cache:l.cache,pendingSuspenseBoundaries:l.pendingSuspenseBoundaries,transitions:l.transitions},t.updateQueue.baseState=a,t.memoizedState=a,t.flags&256){o=Wa(Error(H(423)),t),t=mb(e,t,r,n,o);break e}else if(r!==o){o=Wa(Error(H(424)),t),t=mb(e,t,r,n,o);break e}else for(Ut=Xr(t.stateNode.containerInfo.firstChild),Kt=t,De=!0,Tn=null,n=Tx(t,null,r,n),t.child=n;n;)n.flags=n.flags&-3|4096,n=n.sibling;else{if(Ma(),r===o){t=wr(e,t,n);break e}Pt(e,t,r,n)}t=t.child}return t;case 5:return Px(t),e===null&&$f(t),r=t.type,o=t.pendingProps,a=e!==null?e.memoizedProps:null,l=o.children,zf(r,o)?l=null:a!==null&&zf(r,a)&&(t.flags|=32),ey(e,t),Pt(e,t,l,n),t.child;case 6:return e===null&&$f(t),null;case 13:return ny(e,t,n);case 4:return Op(t,t.stateNode.containerInfo),r=t.pendingProps,e===null?t.child=Da(t,null,r,n):Pt(e,t,r,n),t.child;case 11:return r=t.type,o=t.pendingProps,o=t.elementType===r?o:Sn(r,o),db(e,t,r,o,n);case 7:return Pt(e,t,t.pendingProps,n),t.child;case 8:return Pt(e,t,t.pendingProps.children,n),t.child;case 12:return Pt(e,t,t.pendingProps.children,n),t.child;case 10:e:{if(r=t.type._context,o=t.pendingProps,a=t.memoizedProps,l=o.value,Be(gc,r._currentValue),r._currentValue=l,a!==null)if(Pn(a.value,l)){if(a.children===o.children&&!zt.current){t=wr(e,t,n);break e}}else for(a=t.child,a!==null&&(a.return=t);a!==null;){var i=a.dependencies;if(i!==null){l=a.child;for(var s=i.firstContext;s!==null;){if(s.context===r){if(a.tag===1){s=hr(-1,n&-n),s.tag=2;var c=a.updateQueue;if(c!==null){c=c.shared;var d=c.pending;d===null?s.next=s:(s.next=d.next,d.next=s),c.pending=s}}a.lanes|=n,s=a.alternate,s!==null&&(s.lanes|=n),Uf(a.return,n,t),i.lanes|=n;break}s=s.next}}else if(a.tag===10)l=a.type===t.type?null:a.child;else if(a.tag===18){if(l=a.return,l===null)throw Error(H(341));l.lanes|=n,i=l.alternate,i!==null&&(i.lanes|=n),Uf(l,n,t),l=a.sibling}else l=a.child;if(l!==null)l.return=a;else for(l=a;l!==null;){if(l===t){l=null;break}if(a=l.sibling,a!==null){a.return=l.return,l=a;break}l=l.return}a=l}Pt(e,t,o.children,n),t=t.child}return t;case 9:return o=t.type,r=t.pendingProps.children,Na(t,n),o=fn(o),r=r(o),t.flags|=1,Pt(e,t,r,n),t.child;case 14:return r=t.type,o=Sn(r,t.pendingProps),o=Sn(r.type,o),fb(e,t,r,o,n);case 15:return Zx(e,t,t.type,t.pendingProps,n);case 17:return r=t.type,o=t.pendingProps,o=t.elementType===r?o:Sn(r,o),Js(e,t),t.tag=1,Wt(r)?(e=!0,pc(t)):e=!1,Na(t,n),Yx(t,r,o),Gf(t,r,o,n),Qf(null,t,r,!0,e,n);case 19:return ry(e,t,n);case 22:return Jx(e,t,n)}throw Error(H(156,t.tag))};function xy(e,t){return Kb(e,t)}function hR(e,t,n,r){this.tag=e,this.key=n,this.sibling=this.child=this.return=this.stateNode=this.type=this.elementType=null,this.index=0,this.ref=null,this.pendingProps=t,this.dependencies=this.memoizedState=this.updateQueue=this.memoizedProps=null,this.mode=r,this.subtreeFlags=this.flags=0,this.deletions=null,this.childLanes=this.lanes=0,this.alternate=null}function un(e,t,n,r){return new hR(e,t,n,r)}function Gp(e){return e=e.prototype,!(!e||!e.isReactComponent)}function bR(e){if(typeof e=="function")return Gp(e)?1:0;if(e!=null){if(e=e.$$typeof,e===fp)return 11;if(e===pp)return 14}return 2}function to(e,t){var n=e.alternate;return n===null?(n=un(e.tag,t,e.key,e.mode),n.elementType=e.elementType,n.type=e.type,n.stateNode=e.stateNode,n.alternate=e,e.alternate=n):(n.pendingProps=t,n.type=e.type,n.flags=0,n.subtreeFlags=0,n.deletions=null),n.flags=e.flags&14680064,n.childLanes=e.childLanes,n.lanes=e.lanes,n.child=e.child,n.memoizedProps=e.memoizedProps,n.memoizedState=e.memoizedState,n.updateQueue=e.updateQueue,t=e.dependencies,n.dependencies=t===null?null:{lanes:t.lanes,firstContext:t.firstContext},n.sibling=e.sibling,n.index=e.index,n.ref=e.ref,n}function nc(e,t,n,r,o,a){var l=2;if(r=e,typeof e=="function")Gp(e)&&(l=1);else if(typeof e=="string")l=5;else e:switch(e){case ba:return Wo(n.children,o,a,t);case dp:l=8,o|=8;break;case hf:return e=un(12,n,t,o|2),e.elementType=hf,e.lanes=a,e;case bf:return e=un(13,n,t,o),e.elementType=bf,e.lanes=a,e;case xf:return e=un(19,n,t,o),e.elementType=xf,e.lanes=a,e;case Pb:return Mc(n,o,a,t);default:if(typeof e=="object"&&e!==null)switch(e.$$typeof){case Rb:l=10;break e;case Eb:l=9;break e;case fp:l=11;break e;case pp:l=14;break e;case Vr:l=16,r=null;break e}throw Error(H(130,e==null?e:typeof e,""))}return t=un(l,n,t,o),t.elementType=e,t.type=r,t.lanes=a,t}function Wo(e,t,n,r){return e=un(7,e,r,t),e.lanes=n,e}function Mc(e,t,n,r){return e=un(22,e,r,t),e.elementType=Pb,e.lanes=n,e.stateNode={isHidden:!1},e}function mf(e,t,n){return e=un(6,e,null,t),e.lanes=n,e}function vf(e,t,n){return t=un(4,e.children!==null?e.children:[],e.key,t),t.lanes=n,t.stateNode={containerInfo:e.containerInfo,pendingChildren:null,implementation:e.implementation},t}function xR(e,t,n,r,o){this.tag=t,this.containerInfo=e,this.finishedWork=this.pingCache=this.current=this.pendingChildren=null,this.timeoutHandle=-1,this.callbackNode=this.pendingContext=this.context=null,this.callbackPriority=0,this.eventTimes=Xd(0),this.expirationTimes=Xd(-1),this.entangledLanes=this.finishedLanes=this.mutableReadLanes=this.expiredLanes=this.pingedLanes=this.suspendedLanes=this.pendingLanes=0,this.entanglements=Xd(0),this.identifierPrefix=r,this.onRecoverableError=o,this.mutableSourceEagerHydrationData=null}function qp(e,t,n,r,o,a,l,i,s){return e=new xR(e,t,n,i,s),t===1?(t=1,a===!0&&(t|=8)):t=0,a=un(3,null,null,t),e.current=a,a.stateNode=e,a.memoizedState={element:r,isDehydrated:n,cache:null,transitions:null,pendingSuspenseBoundaries:null},Lp(a),e}function yR(e,t,n){var r=3<arguments.length&&arguments[3]!==void 0?arguments[3]:null;return{$$typeof:ha,key:r==null?null:""+r,children:e,containerInfo:t,implementation:n}}function yy(e){if(!e)return ro;e=e._reactInternals;e:{if(Go(e)!==e||e.tag!==1)throw Error(H(170));var t=e;do{switch(t.tag){case 3:t=t.stateNode.context;break e;case 1:if(Wt(t.type)){t=t.stateNode.__reactInternalMemoizedMergedChildContext;break e}}t=t.return}while(t!==null);throw Error(H(171))}if(e.tag===1){var n=e.type;if(Wt(n))return yx(e,n,t)}return t}function wy(e,t,n,r,o,a,l,i,s){return e=qp(n,r,!0,e,o,a,l,i,s),e.context=yy(null),n=e.current,r=_t(),o=eo(n),a=hr(r,o),a.callback=t??null,Zr(n,a,o),e.current.lanes=o,hi(e,o,r),jt(e,r),e}function Dc(e,t,n,r){var o=t.current,a=_t(),l=eo(o);return n=yy(n),t.context===null?t.context=n:t.pendingContext=n,t=hr(a,l),t.payload={element:e},r=r===void 0?null:r,r!==null&&(t.callback=r),e=Zr(o,t,l),e!==null&&(En(e,o,l,a),Qs(e,o,l)),l}function Tc(e){if(e=e.current,!e.child)return null;switch(e.child.tag){case 5:return e.child.stateNode;default:return e.child.stateNode}}function Sb(e,t){if(e=e.memoizedState,e!==null&&e.dehydrated!==null){var n=e.retryLane;e.retryLane=n!==0&&n<t?n:t}}function Yp(e,t){Sb(e,t),(e=e.alternate)&&Sb(e,t)}function wR(){return null}var Iy=typeof reportError=="function"?reportError:function(e){console.error(e)};function Qp(e){this._internalRoot=e}zc.prototype.render=Qp.prototype.render=function(e){var t=this._internalRoot;if(t===null)throw Error(H(409));Dc(e,t,null,null)};zc.prototype.unmount=Qp.prototype.unmount=function(){var e=this._internalRoot;if(e!==null){this._internalRoot=null;var t=e.containerInfo;Uo(function(){Dc(null,e,null,null)}),t[xr]=null}};function zc(e){this._internalRoot=e}zc.prototype.unstable_scheduleHydration=function(e){if(e){var t=Jb();e={blockedOn:null,target:e,priority:t};for(var n=0;n<$r.length&&t!==0&&t<$r[n].priority;n++);$r.splice(n,0,e),n===0&&tx(e)}};function Xp(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11)}function Wc(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11&&(e.nodeType!==8||e.nodeValue!==" react-mount-point-unstable "))}function kb(){}function IR(e,t,n,r,o){if(o){if(typeof r=="function"){var a=r;r=function(){var c=Tc(l);a.call(c)}}var l=wy(t,r,e,0,null,!1,!1,"",kb);return e._reactRootContainer=l,e[xr]=l.current,si(e.nodeType===8?e.parentNode:e),Uo(),l}for(;o=e.lastChild;)e.removeChild(o);if(typeof r=="function"){var i=r;r=function(){var c=Tc(s);i.call(c)}}var s=qp(e,0,!1,null,null,!1,!1,"",kb);return e._reactRootContainer=s,e[xr]=s.current,si(e.nodeType===8?e.parentNode:e),Uo(function(){Dc(t,s,n,r)}),s}function jc(e,t,n,r,o){var a=n._reactRootContainer;if(a){var l=a;if(typeof o=="function"){var i=o;o=function(){var s=Tc(l);i.call(s)}}Dc(t,l,e,o)}else l=IR(n,t,e,o,r);return Tc(l)}Xb=function(e){switch(e.tag){case 3:var t=e.stateNode;if(t.current.memoizedState.isDehydrated){var n=Hl(t.pendingLanes);n!==0&&(gp(t,n|1),jt(t,Xe()),(Te&6)===0&&(ja=Xe()+500,lo()))}break;case 13:Uo(function(){var r=yr(e,1);if(r!==null){var o=_t();En(r,e,1,o)}}),Yp(e,1)}};hp=function(e){if(e.tag===13){var t=yr(e,134217728);if(t!==null){var n=_t();En(t,e,134217728,n)}Yp(e,134217728)}};Zb=function(e){if(e.tag===13){var t=eo(e),n=yr(e,t);if(n!==null){var r=_t();En(n,e,t,r)}Yp(e,t)}};Jb=function(){return Pe};ex=function(e,t){var n=Pe;try{return Pe=e,t()}finally{Pe=n}};Pf=function(e,t,n){switch(t){case"input":if(If(e,n),t=n.name,n.type==="radio"&&t!=null){for(n=e;n.parentNode;)n=n.parentNode;for(n=n.querySelectorAll("input[name="+JSON.stringify(""+t)+'][type="radio"]'),t=0;t<n.length;t++){var r=n[t];if(r!==e&&r.form===e.form){var o=Lc(r);if(!o)throw Error(H(90));Lb(r),If(r,o)}}}break;case"textarea":Nb(e,n);break;case"select":t=n.value,t!=null&&Pa(e,!!n.multiple,t,!1)}};Wb=$p;jb=Uo;var CR={usingClientEntryPoint:!1,Events:[xi,Ia,Lc,Db,zb,$p]},zl={findFiberByHostInstance:Fo,bundleType:0,version:"18.3.1",rendererPackageName:"react-dom"},SR={bundleType:zl.bundleType,version:zl.version,rendererPackageName:zl.rendererPackageName,rendererConfig:zl.rendererConfig,overrideHookState:null,overrideHookStateDeletePath:null,overrideHookStateRenamePath:null,overrideProps:null,overridePropsDeletePath:null,overridePropsRenamePath:null,setErrorHandler:null,setSuspenseHandler:null,scheduleUpdate:null,currentDispatcherRef:Ir.ReactCurrentDispatcher,findHostInstanceByFiber:function(e){return e=$b(e),e===null?null:e.stateNode},findFiberByHostInstance:zl.findFiberByHostInstance||wR,findHostInstancesForRefresh:null,scheduleRefresh:null,scheduleRoot:null,setRefreshHandler:null,getCurrentFiber:null,reconcilerVersion:"18.3.1-next-f1338f8080-20240426"};if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<"u"&&(Wl=__REACT_DEVTOOLS_GLOBAL_HOOK__,!Wl.isDisabled&&Wl.supportsFiber))try{Rc=Wl.inject(SR),Yn=Wl}catch{}var Wl;Yt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED=CR;Yt.createPortal=function(e,t){var n=2<arguments.length&&arguments[2]!==void 0?arguments[2]:null;if(!Xp(t))throw Error(H(200));return yR(e,t,null,n)};Yt.createRoot=function(e,t){if(!Xp(e))throw Error(H(299));var n=!1,r="",o=Iy;return t!=null&&(t.unstable_strictMode===!0&&(n=!0),t.identifierPrefix!==void 0&&(r=t.identifierPrefix),t.onRecoverableError!==void 0&&(o=t.onRecoverableError)),t=qp(e,1,!1,null,null,n,!1,r,o),e[xr]=t.current,si(e.nodeType===8?e.parentNode:e),new Qp(t)};Yt.findDOMNode=function(e){if(e==null)return null;if(e.nodeType===1)return e;var t=e._reactInternals;if(t===void 0)throw typeof e.render=="function"?Error(H(188)):(e=Object.keys(e).join(","),Error(H(268,e)));return e=$b(t),e=e===null?null:e.stateNode,e};Yt.flushSync=function(e){return Uo(e)};Yt.hydrate=function(e,t,n){if(!Wc(t))throw Error(H(200));return jc(null,e,t,!0,n)};Yt.hydrateRoot=function(e,t,n){if(!Xp(e))throw Error(H(405));var r=n!=null&&n.hydratedSources||null,o=!1,a="",l=Iy;if(n!=null&&(n.unstable_strictMode===!0&&(o=!0),n.identifierPrefix!==void 0&&(a=n.identifierPrefix),n.onRecoverableError!==void 0&&(l=n.onRecoverableError)),t=wy(t,null,e,1,n??null,o,!1,a,l),e[xr]=t.current,si(e),r)for(e=0;e<r.length;e++)n=r[e],o=n._getVersion,o=o(n._source),t.mutableSourceEagerHydrationData==null?t.mutableSourceEagerHydrationData=[n,o]:t.mutableSourceEagerHydrationData.push(n,o);return new zc(t)};Yt.render=function(e,t,n){if(!Wc(t))throw Error(H(200));return jc(null,e,t,!1,n)};Yt.unmountComponentAtNode=function(e){if(!Wc(e))throw Error(H(40));return e._reactRootContainer?(Uo(function(){jc(null,null,e,!1,function(){e._reactRootContainer=null,e[xr]=null})}),!0):!1};Yt.unstable_batchedUpdates=$p;Yt.unstable_renderSubtreeIntoContainer=function(e,t,n,r){if(!Wc(n))throw Error(H(200));if(e==null||e._reactInternals===void 0)throw Error(H(38));return jc(e,t,n,!1,r)};Yt.version="18.3.1-next-f1338f8080-20240426"});var wi=wn((D2,ky)=>{"use strict";function Sy(){if(!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__>"u"||typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE!="function"))try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(Sy)}catch(e){console.error(e)}}Sy(),ky.exports=Cy()});var Ry=wn(Zp=>{"use strict";var Ty=wi();Zp.createRoot=Ty.createRoot,Zp.hydrateRoot=Ty.hydrateRoot;var z2});var Py=wn(Vc=>{"use strict";var kR=E(),TR=Symbol.for("react.element"),RR=Symbol.for("react.fragment"),ER=Object.prototype.hasOwnProperty,PR=kR.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,_R={key:!0,ref:!0,__self:!0,__source:!0};function Ey(e,t,n){var r,o={},a=null,l=null;n!==void 0&&(a=""+n),t.key!==void 0&&(a=""+t.key),t.ref!==void 0&&(l=t.ref);for(r in t)ER.call(t,r)&&!_R.hasOwnProperty(r)&&(o[r]=t[r]);if(e&&e.defaultProps)for(r in t=e.defaultProps,t)o[r]===void 0&&(o[r]=t[r]);return{$$typeof:TR,type:e,key:a,ref:l,props:o,_owner:PR.current}}Vc.Fragment=RR;Vc.jsx=Ey;Vc.jsxs=Ey});var F=wn((V2,_y)=>{"use strict";_y.exports=Py()});var SI=wn(CI=>{"use strict";var cl=E();function LP(e,t){return e===t&&(e!==0||1/e===1/t)||e!==e&&t!==t}var OP=typeof Object.is=="function"?Object.is:LP,NP=cl.useState,BP=cl.useEffect,AP=cl.useLayoutEffect,FP=cl.useDebugValue;function MP(e,t){var n=t(),r=NP({inst:{value:n,getSnapshot:t}}),o=r[0].inst,a=r[1];return AP(function(){o.value=n,o.getSnapshot=t,zv(o)&&a({inst:o})},[e,n,t]),BP(function(){return zv(o)&&a({inst:o}),e(function(){zv(o)&&a({inst:o})})},[e]),FP(n),n}function zv(e){var t=e.getSnapshot;e=e.value;try{var n=t();return!OP(e,n)}catch{return!0}}function DP(e,t){return t()}var zP=typeof window>"u"||typeof window.document>"u"||typeof window.document.createElement>"u"?DP:MP;CI.useSyncExternalStore=cl.useSyncExternalStore!==void 0?cl.useSyncExternalStore:zP});var TI=wn((dA,kI)=>{"use strict";kI.exports=SI()});var Q=w(E()),JS=w(Ry());var LR=w(F()),Hc=w(E()),OR=(0,Hc.createContext)(void 0);function Ly(e){let t=(0,Hc.useContext)(OR);return e??t}var Oy=w(F()),$c=w(E()),Ny=(0,$c.createContext)(!0);function Uc(e){let t=(0,$c.useContext)(Ny);return e??t}function Kc(e){let{value:t,children:n}=e,r=Uc(t);return(0,Oy.jsx)(Ny.Provider,{value:r,children:n})}var NR=w(F()),Ii=w(E()),BR=(0,Ii.createContext)(null);function By(){return(0,Ii.useContext)(BR)}var qc=w(E());var AR=qc.useInsertionEffect??qc.useLayoutEffect,Gc=new WeakMap;function FR(e,t){return JSON.stringify([t??null,e])}function J({testId:e,css:t,nonce:n,window:r}){let o=Uc(),a=By(),l=Ly(n);AR(()=>{if(!r||!o)return;let i=FR(t,l),s=Gc.get(r)??new Map,c=s.get(i)??{styleElement:null,count:0};return c.styleElement==null?(c.styleElement=r.document.createElement("style"),c.styleElement.setAttribute("type","text/css"),c.styleElement.setAttribute("data-salt-style",e||""),l&&(c.styleElement.nonce=l),c.styleElement.textContent=t,c.count=1,r.document.head.insertBefore(c.styleElement,a||r.document.head.firstChild)):c.count++,s.set(i,c),Gc.set(r,s),()=>{let d=Gc.get(r),p=d?.get(i);p?.styleElement&&(p.count--,p.count<1&&(p.styleElement.remove(),p.styleElement=null,d?.delete(i),d?.size===0&&Gc.delete(r)))}},[e,t,l,r,o,a])}var MR=w(F());function Ay(e){var t,n,r="";if(typeof e=="string"||typeof e=="number")r+=e;else if(typeof e=="object")if(Array.isArray(e)){var o=e.length;for(t=0;t<o;t++)e[t]&&(n=Ay(e[t]))&&(r&&(r+=" "),r+=n)}else for(n in e)e[n]&&(r&&(r+=" "),r+=n);return r}function V(){for(var e,t,n=0,r="",o=arguments.length;n<o;n++)(e=arguments[n])&&(t=Ay(e))&&(r&&(r+=" "),r+=t);return r}var Fy=V;var Xn=w(E()),DR=new Map,zR=(0,Xn.createContext)(DR);function _n(e,t){let r=(0,Xn.useContext)(zR).get(e)??[],o=(0,Xn.useMemo)(()=>r.length?r.flatMap(s=>s.keys.map(c=>t[c])):[],[r,t]),a=(0,Xn.useMemo)(()=>{let{className:s,...c}=t;return r.length?r.map(d=>({entry:d,result:d.fn(c)??null})):[]},[r,o,t]),l=(0,Xn.useMemo)(()=>V(t.className,a.map(s=>s.result).filter(s=>s!=null))||void 0,[t,a]),i=(0,Xn.useMemo)(()=>{let{className:s,...c}=t;if(!r.length)return c;let d={...c};for(let{entry:p,result:g}of a)if(g!=null)for(let m of p.keys)Object.hasOwn(d,m)&&delete d[m];return d},[r,a,t]);return{className:l,props:i}}var WR=w(F()),Yc=w(E()),jR=(0,Yc.createContext)(typeof window<"u"?window:null);function Y(){return(0,Yc.useContext)(jR)}var te=e=>(...t)=>[e,...t].join("-");var mn=w(E());function Ot({controlled:e,default:t,name:n,state:r="value"}){let{current:o}=(0,mn.useRef)(e!==void 0),[a,l]=(0,mn.useState)(t),i=e!==void 0?e:a,{current:s}=(0,mn.useRef)(t);(0,mn.useEffect)(()=>{},[r,n,e]),(0,mn.useEffect)(()=>{},[JSON.stringify(t,VR)]);let c=(0,mn.useCallback)(d=>{o||l(d)},[]);return[i,c,o]}function VR(e,t){return(0,mn.isValidElement)(t)?null:t}var po=w(F());var q=w(E(),1);function Qc(){return typeof window<"u"}function Jn(e){return Xc(e)?(e.nodeName||"").toLowerCase():"#document"}function mt(e){var t;return(e==null||(t=e.ownerDocument)==null?void 0:t.defaultView)||window}function er(e){var t;return(t=(Xc(e)?e.ownerDocument:e.document)||window.document)==null?void 0:t.documentElement}function Xc(e){return Qc()?e instanceof Node||e instanceof mt(e).Node:!1}function ze(e){return Qc()?e instanceof Element||e instanceof mt(e).Element:!1}function Ze(e){return Qc()?e instanceof HTMLElement||e instanceof mt(e).HTMLElement:!1}function $a(e){return!Qc()||typeof ShadowRoot>"u"?!1:e instanceof ShadowRoot||e instanceof mt(e).ShadowRoot}function Ci(e){let{overflow:t,overflowX:n,overflowY:r,display:o}=Xt(e);return/auto|scroll|overlay|hidden|clip/.test(t+r+n)&&o!=="inline"&&o!=="contents"}function My(e){return/^(table|td|th)$/.test(Jn(e))}function Si(e){try{if(e.matches(":popover-open"))return!0}catch{}try{return e.matches(":modal")}catch{return!1}}var HR=/transform|translate|scale|rotate|perspective|filter/,$R=/paint|layout|strict|content/,qo=e=>!!e&&e!=="none",Jp;function Zc(e){let t=ze(e)?Xt(e):e;return qo(t.transform)||qo(t.translate)||qo(t.scale)||qo(t.rotate)||qo(t.perspective)||!Ua()&&(qo(t.backdropFilter)||qo(t.filter))||HR.test(t.willChange||"")||$R.test(t.contain||"")}function Dy(e){let t=Zn(e);for(;Ze(t)&&!tr(t);){if(Zc(t))return t;if(Si(t))return null;t=Zn(t)}return null}function Ua(){return Jp==null&&(Jp=typeof CSS<"u"&&CSS.supports&&CSS.supports("-webkit-backdrop-filter","none")),Jp}function tr(e){return/^(html|body|#document)$/.test(Jn(e))}function Xt(e){return mt(e).getComputedStyle(e)}function ki(e){return ze(e)?{scrollLeft:e.scrollLeft,scrollTop:e.scrollTop}:{scrollLeft:e.scrollX,scrollTop:e.scrollY}}function Zn(e){if(Jn(e)==="html")return e;let t=e.assignedSlot||e.parentNode||$a(e)&&e.host||er(e);return $a(t)?t.host:t}function zy(e){let t=Zn(e);return tr(t)?(e.ownerDocument||e).body:Ze(t)&&Ci(t)?t:zy(t)}function Qt(e,t,n){var r;t===void 0&&(t=[]),n===void 0&&(n=!0);let o=zy(e),a=o===((r=e.ownerDocument)==null?void 0:r.body),l=mt(o);if(a){let i=Jc(l);return t.concat(l,l.visualViewport||[],Ci(o)?o:[],i&&n?Qt(i):[])}else return t.concat(o,Qt(o,[],n))}function Jc(e){return e.parent&&Object.getPrototypeOf(e.parent)?e.frameElement:null}var qa=w(E(),1),n0=w(E(),1);var io=Math.min,Ln=Math.max,Ri=Math.round,Ei=Math.floor,nr=e=>({x:e,y:e}),UR={left:"right",right:"left",bottom:"top",top:"bottom"};function Vy(e,t,n){return Ln(e,io(t,n))}function so(e,t){return typeof e=="function"?e(t):e}function Cr(e){return e.split("-")[0]}function Ka(e){return e.split("-")[1]}function tu(e){return e==="x"?"y":"x"}function em(e){return e==="y"?"height":"width"}function On(e){let t=e[0];return t==="t"||t==="b"?"y":"x"}function tm(e){return tu(On(e))}function Hy(e,t,n){n===void 0&&(n=!1);let r=Ka(e),o=tm(e),a=em(o),l=o==="x"?r===(n?"end":"start")?"right":"left":r==="start"?"bottom":"top";return t.reference[a]>t.floating[a]&&(l=Ti(l)),[l,Ti(l)]}function $y(e){let t=Ti(e);return[eu(e),t,eu(t)]}function eu(e){return e.includes("start")?e.replace("start","end"):e.replace("end","start")}var Wy=["left","right"],jy=["right","left"],KR=["top","bottom"],GR=["bottom","top"];function qR(e,t,n){switch(e){case"top":case"bottom":return n?t?jy:Wy:t?Wy:jy;case"left":case"right":return t?KR:GR;default:return[]}}function Uy(e,t,n,r){let o=Ka(e),a=qR(Cr(e),n==="start",r);return o&&(a=a.map(l=>l+"-"+o),t&&(a=a.concat(a.map(eu)))),a}function Ti(e){let t=Cr(e);return UR[t]+e.slice(t.length)}function YR(e){var t,n,r,o;return{top:(t=e.top)!=null?t:0,right:(n=e.right)!=null?n:0,bottom:(r=e.bottom)!=null?r:0,left:(o=e.left)!=null?o:0}}function Ky(e){return typeof e!="number"?YR(e):{top:e,right:e,bottom:e,left:e}}function Yo(e){let{x:t,y:n,width:r,height:o}=e;return{width:r,height:o,top:n,left:t,right:t+r,bottom:n+o,x:t,y:n}}var QR=["input:not([inert]):not([inert] *)","select:not([inert]):not([inert] *)","textarea:not([inert]):not([inert] *)","a[href]:not([inert]):not([inert] *)","area[href]:not([inert]):not([inert] *)","button:not([inert]):not([inert] *)","[tabindex]:not(slot):not([inert]):not([inert] *)","audio[controls]:not([inert]):not([inert] *)","video[controls]:not([inert]):not([inert] *)",'[contenteditable]:not([contenteditable="false"]):not([inert]):not([inert] *)',"details>summary:first-of-type:not([inert]):not([inert] *)","details:not([inert]):not([inert] *)"],nu=QR.join(","),qy=typeof Element>"u",Ga=qy?function(){}:Element.prototype.matches||Element.prototype.msMatchesSelector||Element.prototype.webkitMatchesSelector,ru=!qy&&Element.prototype.getRootNode?function(e){var t;return e==null||(t=e.getRootNode)===null||t===void 0?void 0:t.call(e)}:function(e){return e?.ownerDocument},ou=function(t,n){var r;n===void 0&&(n=!0);var o=t==null||(r=t.getAttribute)===null||r===void 0?void 0:r.call(t,"inert"),a=o===""||o==="true",l=a||n&&t&&(typeof t.closest=="function"?t.closest("[inert]"):ou(t.parentNode));return l},XR=function(t){var n,r=t==null||(n=t.getAttribute)===null||n===void 0?void 0:n.call(t,"contenteditable");return r===""||r==="true"},Yy=function(t,n,r){if(ou(t))return[];var o=Array.prototype.slice.apply(t.querySelectorAll(nu));return n&&Ga.call(t,nu)&&o.unshift(t),o=o.filter(r),o},au=function(t,n,r){for(var o=[],a=Array.from(t);a.length;){var l=a.shift();if(!ou(l,!1))if(l.tagName==="SLOT"){var i=l.assignedElements(),s=i.length?i:l.children,c=au(s,!0,r);r.flatten?o.push.apply(o,c):o.push({scopeParent:l,candidates:c})}else{var d=Ga.call(l,nu);d&&r.filter(l)&&(n||!t.includes(l))&&o.push(l);var p=l.shadowRoot||typeof r.getShadowRoot=="function"&&r.getShadowRoot(l),g=!ou(p,!1)&&(!r.shadowRootFilter||r.shadowRootFilter(l));if(p&&g){var m=au(p===!0?l.children:p.children,!0,r);r.flatten?o.push.apply(o,m):o.push({scopeParent:l,candidates:m})}else a.unshift.apply(a,l.children)}}return o},Qy=function(t){return!isNaN(parseInt(t.getAttribute("tabindex"),10))},Xy=function(t){if(!t)throw new Error("No node provided");return t.tabIndex<0&&(/^(AUDIO|VIDEO|DETAILS)$/.test(t.tagName)||XR(t))&&!Qy(t)?0:t.tabIndex},ZR=function(t,n){var r=Xy(t);return r<0&&n&&!Qy(t)?0:r},JR=function(t,n){return t.tabIndex===n.tabIndex?t.documentOrder-n.documentOrder:t.tabIndex-n.tabIndex},Zy=function(t){return t.tagName==="INPUT"},eE=function(t){return Zy(t)&&t.type==="hidden"},tE=function(t){var n=t.tagName==="DETAILS"&&Array.prototype.slice.apply(t.children).some(function(r){return r.tagName==="SUMMARY"});return n},nE=function(t,n){for(var r=0;r<t.length;r++)if(t[r].checked&&t[r].form===n)return t[r]},rE=function(t){if(!t.name)return!0;var n=t.form||ru(t),r=function(i){return n.querySelectorAll('input[type="radio"][name="'+i+'"]')},o;if(typeof window<"u"&&typeof window.CSS<"u"&&typeof window.CSS.escape=="function")o=r(window.CSS.escape(t.name));else try{o=r(t.name)}catch(l){return console.error("Looks like you have a radio button with a name attribute containing invalid CSS selector characters and need the CSS.escape polyfill: %s",l.message),!1}var a=nE(o,t.form);return!a||a===t},oE=function(t){return Zy(t)&&t.type==="radio"},aE=function(t){return oE(t)&&!rE(t)},lE=function(t){var n,r=t&&ru(t),o=(n=r)===null||n===void 0?void 0:n.host,a=!1;if(r&&r!==t){var l,i,s;for(a=!!((l=o)!==null&&l!==void 0&&(i=l.ownerDocument)!==null&&i!==void 0&&i.contains(o)||t!=null&&(s=t.ownerDocument)!==null&&s!==void 0&&s.contains(t));!a&&o;){var c,d,p;r=ru(o),o=(c=r)===null||c===void 0?void 0:c.host,a=!!((d=o)!==null&&d!==void 0&&(p=d.ownerDocument)!==null&&p!==void 0&&p.contains(o))}}return a},Gy=function(t){var n=t.getBoundingClientRect(),r=n.width,o=n.height;return r===0&&o===0},iE=function(t,n){var r=n.displayCheck,o=n.getShadowRoot;if(r==="full-native"&&"checkVisibility"in t){var a=t.checkVisibility({checkOpacity:!1,opacityProperty:!1,contentVisibilityAuto:!0,visibilityProperty:!0,checkVisibilityCSS:!0});return!a}var l=getComputedStyle(t),i=l.visibility;if(i==="hidden"||i==="collapse")return!0;var s=Ga.call(t,"details>summary:first-of-type"),c=s?t.parentElement:t;if(Ga.call(c,"details:not([open]) *"))return!0;if(!r||r==="full"||r==="full-native"||r==="legacy-full"){if(typeof o=="function"){for(var d=t;t;){var p=t.parentElement,g=ru(t);if(p&&!p.shadowRoot&&o(p)===!0)return Gy(t);t.assignedSlot?t=t.assignedSlot:!p&&g!==t.ownerDocument?t=g.host:t=p}t=d}if(lE(t))return!t.getClientRects().length;if(r!=="legacy-full")return!0}else if(r==="non-zero-area")return Gy(t);return!1},sE=function(t){if(/^(INPUT|BUTTON|SELECT|TEXTAREA)$/.test(t.tagName))for(var n=t.parentElement;n;){if(n.tagName==="FIELDSET"&&n.disabled){for(var r=0;r<n.children.length;r++){var o=n.children.item(r);if(o.tagName==="LEGEND")return Ga.call(n,"fieldset[disabled] *")?!0:!o.contains(t)}return!0}n=n.parentElement}return!1},nm=function(t,n){return!(n.disabled||eE(n)||iE(n,t)||tE(n)||sE(n))},rm=function(t,n){return!(aE(n)||Xy(n)<0||!nm(t,n))},cE=function(t){var n=parseInt(t.getAttribute("tabindex"),10);return!!(isNaN(n)||n>=0)},Jy=function(t){var n=[],r=[];return t.forEach(function(o,a){var l=!!o.scopeParent,i=l?o.scopeParent:o,s=ZR(i,l),c=l?Jy(o.candidates):i;s===0?l?n.push.apply(n,c):n.push(i):r.push({documentOrder:a,tabIndex:s,item:o,isScope:l,content:c})}),r.sort(JR).reduce(function(o,a){return a.isScope?o.push.apply(o,a.content):o.push(a.content),o},[]).concat(n)},co=function(t,n){n=n||{};var r;return n.getShadowRoot?r=au([t],n.includeContainer,{filter:rm.bind(null,n),flatten:!1,getShadowRoot:n.getShadowRoot,shadowRootFilter:cE}):r=Yy(t,n.includeContainer,rm.bind(null,n)),Jy(r)},e0=function(t,n){n=n||{};var r;return n.getShadowRoot?r=au([t],n.includeContainer,{filter:nm.bind(null,n),flatten:!0,getShadowRoot:n.getShadowRoot}):r=Yy(t,n.includeContainer,nm.bind(null,n)),r},om=function(t,n){if(n=n||{},!t)throw new Error("No node provided");return Ga.call(t,nu)===!1?!1:rm(n,t)};function lm(){let e=navigator.userAgentData;return e!=null&&e.platform?e.platform:navigator.platform}function im(){let e=navigator.userAgentData;return e&&Array.isArray(e.brands)?e.brands.map(t=>{let{brand:n,version:r}=t;return n+"/"+r}).join(" "):navigator.userAgent}function sm(){return/apple/i.test(navigator.vendor)}function am(){let e=/android/i;return e.test(lm())||e.test(im())}function r0(){return lm().toLowerCase().startsWith("mac")&&!navigator.maxTouchPoints}function o0(){return im().includes("jsdom/")}var t0="data-floating-ui-focusable",uE="input:not([type='hidden']):not([disabled]),[contenteditable]:not([contenteditable='false']),textarea:not([disabled])";function Sr(e){let t=e.activeElement;for(;((n=t)==null||(n=n.shadowRoot)==null?void 0:n.activeElement)!=null;){var n;t=t.shadowRoot.activeElement}return t}function It(e,t){if(!e||!t)return!1;let n=t.getRootNode==null?void 0:t.getRootNode();if(e.contains(t))return!0;if(n&&$a(n)){let r=t;for(;r;){if(e===r)return!0;r=r.parentNode||r.host}}return!1}function rr(e){return"composedPath"in e?e.composedPath()[0]:e.target}function lu(e,t){if(t==null)return!1;if("composedPath"in e)return e.composedPath().includes(t);let n=e;return n.target!=null&&t.contains(n.target)}function a0(e){return e.matches("html,body")}function Zt(e){return e?.ownerDocument||document}function iu(e){return Ze(e)&&e.matches(uE)}function cm(e){return e?e.getAttribute("role")==="combobox"&&iu(e):!1}function l0(e){if(!e||o0())return!0;try{return e.matches(":focus-visible")}catch{return!0}}function um(e){return e?e.hasAttribute(t0)?e:e.querySelector("["+t0+"]")||e:null}function Qo(e,t,n){return n===void 0&&(n=!0),e.filter(o=>{var a;return o.parentId===t&&(!n||((a=o.context)==null?void 0:a.open))}).flatMap(o=>[o,...Qo(e,o.id,n)])}function dm(e,t){var n;let r=[],o=(n=e.find(a=>a.id===t))==null?void 0:n.parentId;for(;o;){let a=e.find(l=>l.id===o);o=a?.parentId,a&&(r=r.concat(a))}return r}function su(e){e.preventDefault(),e.stopPropagation()}function i0(e){return"nativeEvent"in e}function s0(e){return e.mozInputSource===0&&e.isTrusted?!0:am()&&e.pointerType?e.type==="click"&&e.buttons===1:e.detail===0&&!e.pointerType}function c0(e){return o0()?!1:!am()&&e.width===0&&e.height===0||am()&&e.width===1&&e.height===1&&e.pressure===0&&e.detail===0&&e.pointerType==="mouse"||e.width<1&&e.height<1&&e.pressure===0&&e.detail===0&&e.pointerType==="touch"}function fm(e,t){let n=["mouse","pen"];return t||n.push("",void 0),n.includes(e)}var dE=typeof document<"u",fE=function(){},Jt=dE?n0.useLayoutEffect:fE,pE={...qa};function cu(e){let t=qa.useRef(e);return Jt(()=>{t.current=e}),t}var mE=pE.useInsertionEffect,vE=mE||(e=>e());function Nn(e){let t=qa.useRef(()=>{});return vE(()=>{t.current=e}),qa.useCallback(function(){for(var n=arguments.length,r=new Array(n),o=0;o<n;o++)r[o]=arguments[o];return t.current==null?void 0:t.current(...r)},[])}var Ya=()=>({getShadowRoot:!0,displayCheck:typeof ResizeObserver=="function"&&ResizeObserver.toString().includes("[native code]")?"full":"none"});function u0(e,t){let n=co(e,Ya()),r=n.length;if(r===0)return;let o=Sr(Zt(e)),a=n.indexOf(o),l=a===-1?t===1?0:r-1:a+t;return n[l]}function pm(e){return u0(Zt(e).body,1)||e}function mm(e){return u0(Zt(e).body,-1)||e}function Qa(e,t){let n=t||e.currentTarget,r=e.relatedTarget;return!r||!It(n,r)}function d0(e){co(e,Ya()).forEach(n=>{n.dataset.tabindex=n.getAttribute("tabindex")||"",n.setAttribute("tabindex","-1")})}function vm(e){e.querySelectorAll("[data-tabindex]").forEach(n=>{let r=n.dataset.tabindex;delete n.dataset.tabindex,r?n.setAttribute("tabindex",r):n.removeAttribute("tabindex")})}var Vt=w(F(),1);var Cm=w(wi(),1);function f0(e,t,n){let{reference:r,floating:o}=e,a=On(t),l=tm(t),i=em(l),s=Cr(t),c=a==="y",d=r.x+r.width/2-o.width/2,p=r.y+r.height/2-o.height/2,g=r[i]/2-o[i]/2,m;switch(s){case"top":m={x:d,y:r.y-o.height};break;case"bottom":m={x:d,y:r.y+r.height};break;case"right":m={x:r.x+r.width,y:p};break;case"left":m={x:r.x-o.width,y:p};break;default:m={x:r.x,y:r.y}}let b=Ka(t);return b&&(m[l]+=g*(b==="end"?1:-1)*(n&&c?-1:1)),m}async function p0(e,t){var n;t===void 0&&(t={});let{x:r,y:o,platform:a,rects:l,elements:i,strategy:s}=e,{boundary:c="clippingAncestors",rootBoundary:d="viewport",elementContext:p="floating",altBoundary:g=!1,padding:m=0}=so(t,e),b=Ky(m),y=i[g?p==="floating"?"reference":"floating":p],v=Yo(await a.getClippingRect({element:(n=await(a.isElement==null?void 0:a.isElement(y)))==null||n?y:y.contextElement||await(a.getDocumentElement==null?void 0:a.getDocumentElement(i.floating)),boundary:c,rootBoundary:d,strategy:s})),u=p==="floating"?{x:r,y:o,width:l.floating.width,height:l.floating.height}:l.reference,f=await(a.getOffsetParent==null?void 0:a.getOffsetParent(i.floating)),x=await(a.isElement==null?void 0:a.isElement(f))&&await(a.getScale==null?void 0:a.getScale(f))||{x:1,y:1},I=Yo(a.convertOffsetParentRelativeRectToViewportRelativeRect?await a.convertOffsetParentRelativeRectToViewportRelativeRect({elements:i,rect:u,offsetParent:f,strategy:s}):u);return{top:(v.top-I.top+b.top)/x.y,bottom:(I.bottom-v.bottom+b.bottom)/x.y,left:(v.left-I.left+b.left)/x.x,right:(I.right-v.right+b.right)/x.x}}var gE=50,m0=async(e,t,n)=>{let{placement:r="bottom",strategy:o="absolute",middleware:a=[],platform:l}=n,i=l.detectOverflow?l:{...l,detectOverflow:p0},s=await(l.isRTL==null?void 0:l.isRTL(t)),c=await l.getElementRects({reference:e,floating:t,strategy:o}),{x:d,y:p}=f0(c,r,s),g=r,m=0,b={};for(let h=0;h<a.length;h++){let y=a[h];if(!y)continue;let{name:v,fn:u}=y,{x:f,y:x,data:I,reset:C}=await u({x:d,y:p,initialPlacement:r,placement:g,strategy:o,middlewareData:b,rects:c,platform:i,elements:{reference:e,floating:t}});d=f??d,p=x??p,b[v]={...b[v],...I},C&&m<gE&&(m++,typeof C=="object"&&(C.placement&&(g=C.placement),C.rects&&(c=C.rects===!0?await l.getElementRects({reference:e,floating:t,strategy:o}):C.rects),{x:d,y:p}=f0(c,g,s)),h=-1)}return{x:d,y:p,placement:g,strategy:o,middlewareData:b}};var v0=function(e){return e===void 0&&(e={}),{name:"flip",options:e,async fn(t){var n,r;let{placement:o,middlewareData:a,rects:l,initialPlacement:i,platform:s,elements:c}=t,{mainAxis:d=!0,crossAxis:p=!0,fallbackPlacements:g,fallbackStrategy:m="bestFit",fallbackAxisSideDirection:b="none",flipAlignment:h=!0,...y}=so(e,t);if((n=a.arrow)!=null&&n.alignmentOffset)return{};let v=Cr(o),u=On(i),f=Cr(i)===i,x=await(s.isRTL==null?void 0:s.isRTL(c.floating)),I=g||(f||!h?[Ti(i)]:$y(i)),C=b!=="none";!g&&C&&I.push(...Uy(i,h,b,x));let k=[i,...I],T=await s.detectOverflow(t,y),z=[],O=((r=a.flip)==null?void 0:r.overflows)||[];if(d&&z.push(T[v]),p){let N=Hy(o,l,x);z.push(T[N[0]],T[N[1]])}if(O=[...O,{placement:o,overflows:z}],!z.every(N=>N<=0)){var A,B;let N=(((A=a.flip)==null?void 0:A.index)||0)+1,R=k[N];if(R&&(!(p==="alignment"?u!==On(R):!1)||O.every(_=>On(_.placement)===u?_.overflows[0]>0:!0)))return{data:{index:N,overflows:O},reset:{placement:R}};let P=(B=O.filter(j=>j.overflows[0]<=0).sort((j,_)=>j.overflows[1]-_.overflows[1])[0])==null?void 0:B.placement;if(!P)switch(m){case"bestFit":{var D;let j=(D=O.filter(_=>{if(C){let W=On(_.placement);return W===u||W==="y"}return!0}).map(_=>[_.placement,_.overflows.filter(W=>W>0).reduce((W,ee)=>W+ee,0)]).sort((_,W)=>_[1]-W[1])[0])==null?void 0:D[0];j&&(P=j);break}case"initialPlacement":P=i;break}if(o!==P)return{reset:{placement:P}}}return{}}}};var g0=new Set(["left","top"]);async function hE(e,t){let{placement:n,platform:r,elements:o}=e,a=await(r.isRTL==null?void 0:r.isRTL(o.floating)),l=Cr(n),i=Ka(n),s=On(n)==="y",c=g0.has(l)?-1:1,d=a&&s?-1:1,p=so(t,e),{mainAxis:g,crossAxis:m,alignmentAxis:b}=typeof p=="number"?{mainAxis:p,crossAxis:0,alignmentAxis:null}:{mainAxis:p.mainAxis||0,crossAxis:p.crossAxis||0,alignmentAxis:p.alignmentAxis};return i&&typeof b=="number"&&(m=i==="end"?b*-1:b),s?{x:m*d,y:g*c}:{x:g*c,y:m*d}}var h0=function(e){return e===void 0&&(e=0),{name:"offset",options:e,async fn(t){var n,r;let{x:o,y:a,placement:l,middlewareData:i}=t,s=await hE(t,e);return l===((n=i.offset)==null?void 0:n.placement)&&(r=i.arrow)!=null&&r.alignmentOffset?{}:{x:o+s.x,y:a+s.y,data:{...s,placement:l}}}}},b0=function(e){return e===void 0&&(e={}),{name:"shift",options:e,async fn(t){let{x:n,y:r,placement:o,platform:a}=t,{mainAxis:l=!0,crossAxis:i=!1,limiter:s={fn:u=>{let{x:f,y:x}=u;return{x:f,y:x}}},...c}=so(e,t),d={x:n,y:r},p=await a.detectOverflow(t,c),g=On(o),m=tu(g),b=d[m],h=d[g],y=(u,f)=>Vy(f+p[u==="y"?"top":"left"],f,f-p[u==="y"?"bottom":"right"]);l&&(b=y(m,b)),i&&(h=y(g,h));let v=s.fn({...t,[m]:b,[g]:h});return{...v,data:{x:v.x-n,y:v.y-r,enabled:{[m]:l,[g]:i}}}}}},x0=function(e){return e===void 0&&(e={}),{options:e,fn(t){var n,r;let{x:o,y:a,placement:l,rects:i,middlewareData:s}=t,{offset:c=0,mainAxis:d=!0,crossAxis:p=!0}=so(e,t),g={x:o,y:a},m=On(l),b=tu(m),h=g[b],y=g[m],v=so(c,t),u=typeof v=="number"?{mainAxis:v,crossAxis:0}:{mainAxis:(n=v.mainAxis)!=null?n:0,crossAxis:(r=v.crossAxis)!=null?r:0};if(d){let I=b==="y"?"height":"width",C=i.reference[b]-i.floating[I]+u.mainAxis,k=i.reference[b]+i.reference[I]-u.mainAxis;h<C?h=C:h>k&&(h=k)}if(p){var f,x;let I=b==="y"?"width":"height",C=g0.has(Cr(l)),k=i.reference[m]-i.floating[I]+(C&&((f=s.offset)==null?void 0:f[m])||0)+(C?0:u.crossAxis),T=i.reference[m]+i.reference[I]+(C?0:((x=s.offset)==null?void 0:x[m])||0)-(C?u.crossAxis:0);y<k?y=k:y>T&&(y=T)}return{[b]:h,[m]:y}}}},y0=function(e){return e===void 0&&(e={}),{name:"size",options:e,async fn(t){let{placement:n,rects:r,platform:o,elements:a}=t,{apply:l=()=>{},...i}=so(e,t),s=await o.detectOverflow(t,i),c=Cr(n),d=Ka(n),p=On(n)==="y",{width:g,height:m}=r.floating,b,h;c==="top"||c==="bottom"?(b=c,h=d===(await(o.isRTL==null?void 0:o.isRTL(a.floating))?"start":"end")?"left":"right"):(h=c,b=d==="end"?"top":"bottom");let y=m-s.top-s.bottom,v=g-s.left-s.right,u=io(m-s[b],y),f=io(g-s[h],v),x=t.middlewareData.shift,I=!x,C=u,k=f;x!=null&&x.enabled.x&&(k=v),x!=null&&x.enabled.y&&(C=y),I&&!d&&(p?k=g-2*Ln(s.left,s.right):C=m-2*Ln(s.top,s.bottom)),await l({...t,availableWidth:k,availableHeight:C});let T=await o.getDimensions(a.floating);return g!==T.width||m!==T.height?{reset:{rects:!0}}:{}}}};function C0(e){let t=Xt(e),n=parseFloat(t.width)||0,r=parseFloat(t.height)||0,o=Ze(e),a=o?e.offsetWidth:n,l=o?e.offsetHeight:r,i=Ri(n)!==a||Ri(r)!==l;return i&&(n=a,r=l),{width:n,height:r,$:i}}function hm(e){return ze(e)?e:e.contextElement}function Xa(e){let t=hm(e);if(!Ze(t))return nr(1);let n=t.getBoundingClientRect(),{width:r,height:o,$:a}=C0(t),l=(a?Ri(n.width):n.width)/r,i=(a?Ri(n.height):n.height)/o;return(!l||!Number.isFinite(l))&&(l=1),(!i||!Number.isFinite(i))&&(i=1),{x:l,y:i}}var bE=nr(0);function S0(e){let t=mt(e);return!Ua()||!t.visualViewport?bE:{x:t.visualViewport.offsetLeft,y:t.visualViewport.offsetTop}}function xE(e,t,n){return t===void 0&&(t=!1),!!n&&t&&n===mt(e)}function Xo(e,t,n,r){t===void 0&&(t=!1),n===void 0&&(n=!1);let o=e.getBoundingClientRect(),a=hm(e),l=nr(1);t&&(r?ze(r)&&(l=Xa(r)):l=Xa(e));let i=xE(a,n,r)?S0(a):nr(0),s=(o.left+i.x)/l.x,c=(o.top+i.y)/l.y,d=o.width/l.x,p=o.height/l.y;if(a&&r){let g=mt(a),m=ze(r)?mt(r):r,b=g,h=Jc(b);for(;h&&m!==b;){let y=Xa(h),v=h.getBoundingClientRect(),u=Xt(h),f=v.left+(h.clientLeft+parseFloat(u.paddingLeft))*y.x,x=v.top+(h.clientTop+parseFloat(u.paddingTop))*y.y;s*=y.x,c*=y.y,d*=y.x,p*=y.y,s+=f,c+=x,b=mt(h),h=Jc(b)}}return Yo({width:d,height:p,x:s,y:c})}function uu(e,t){let n=ki(e).scrollLeft;return t?t.left+n:Xo(er(e)).left+n}function k0(e,t){let n=e.getBoundingClientRect(),r=n.left+t.scrollLeft-uu(e,n),o=n.top+t.scrollTop;return{x:r,y:o}}function yE(e){let{elements:t,rect:n,offsetParent:r,strategy:o}=e,a=o==="fixed",l=er(r),i=t?Si(t.floating):!1;if(r===l||i&&a)return n;let s={scrollLeft:0,scrollTop:0},c=nr(1),d=nr(0),p=Ze(r);if((p||!a)&&((Jn(r)!=="body"||Ci(l))&&(s=ki(r)),p)){let m=Xo(r);c=Xa(r),d.x=m.x+r.clientLeft,d.y=m.y+r.clientTop}let g=l&&!p&&!a?k0(l,s):nr(0);return{width:n.width*c.x,height:n.height*c.y,x:n.x*c.x-s.scrollLeft*c.x+d.x+g.x,y:n.y*c.y-s.scrollTop*c.y+d.y+g.y}}function wE(e){return e.getClientRects?Array.from(e.getClientRects()):[]}function IE(e){let t=ki(e),n=e.ownerDocument.body,r=Ln(e.scrollWidth,e.clientWidth,n.scrollWidth,n.clientWidth),o=Ln(e.scrollHeight,e.clientHeight,n.scrollHeight,n.clientHeight),a=-t.scrollLeft+uu(e),l=-t.scrollTop;return Xt(n).direction==="rtl"&&(a+=Ln(e.clientWidth,n.clientWidth)-r),{width:r,height:o,x:a,y:l}}var CE=25;function SE(e,t,n){n===void 0&&(n="viewport");let r=n==="layoutViewport",o=mt(e),a=er(e),l=o.visualViewport,i=a.clientWidth,s=a.clientHeight,c=0,d=0;if(l){let g=!Ua()||t==="fixed";r?g||(c=-l.offsetLeft,d=-l.offsetTop):(i=l.width,s=l.height,g&&(c=l.offsetLeft,d=l.offsetTop))}if(uu(a)<=0){let g=a.ownerDocument,m=g.body,b=getComputedStyle(m),h=g.compatMode==="CSS1Compat"&&parseFloat(b.marginLeft)+parseFloat(b.marginRight)||0,y=Math.abs(a.clientWidth-m.clientWidth-h),v=getComputedStyle(a).scrollbarGutter==="stable both-edges"?y/2:y;v<=CE&&(i-=v)}return{width:i,height:s,x:c,y:d}}function kE(e,t){let n=Xo(e,!0,t==="fixed"),r=n.top+e.clientTop,o=n.left+e.clientLeft,a=Xa(e),l=e.clientWidth*a.x,i=e.clientHeight*a.y,s=o*a.x,c=r*a.y;return{width:l,height:i,x:s,y:c}}function w0(e,t,n){let r;if(t==="viewport"||t==="layoutViewport")r=SE(e,n,t);else if(t==="document")r=IE(er(e));else if(ze(t))r=kE(t,n);else{let o=S0(e);r={x:t.x-o.x,y:t.y-o.y,width:t.width,height:t.height}}return Yo(r)}function TE(e,t){let n=t.get(e);if(n)return n;let r=Qt(e,[],!1).filter(i=>ze(i)&&Jn(i)!=="body"),o=null,a=Xt(e).position==="fixed",l=a?Zn(e):e;for(;ze(l)&&!tr(l);){let i=Xt(l),s=Zc(l),c=o?o.position:a?"fixed":"";!s&&(c==="fixed"||c==="absolute"&&i.position==="static")?r=r.filter(p=>p!==l):o=i,l=Zn(l)}return t.set(e,r),r}function RE(e){let{element:t,boundary:n,rootBoundary:r,strategy:o}=e,l=[...n==="clippingAncestors"?Si(t)?[]:TE(t,this._c):[].concat(n),r],i=w0(t,l[0],o),s=i.top,c=i.right,d=i.bottom,p=i.left;for(let g=1;g<l.length;g++){let m=w0(t,l[g],o);s=Ln(m.top,s),c=io(m.right,c),d=io(m.bottom,d),p=Ln(m.left,p)}return{width:c-p,height:d-s,x:p,y:s}}function EE(e){let{width:t,height:n}=C0(e);return{width:t,height:n}}function PE(e,t,n){let r=Ze(t),o=er(t),a=n==="fixed",l=Xo(e,!0,a,t),i={scrollLeft:0,scrollTop:0},s=nr(0);if((r||!a)&&((Jn(t)!=="body"||Ci(o))&&(i=ki(t)),r)){let g=Xo(t,!0,a,t);s.x=g.x+t.clientLeft,s.y=g.y+t.clientTop}!r&&o&&(s.x=uu(o));let c=o&&!r&&!a?k0(o,i):nr(0),d=l.left+i.scrollLeft-s.x-c.x,p=l.top+i.scrollTop-s.y-c.y;return{x:d,y:p,width:l.width,height:l.height}}function gm(e){return Xt(e).position==="static"}function I0(e,t){if(!Ze(e)||Xt(e).position==="fixed")return null;if(t)return t(e);let n=e.offsetParent;return er(e)===n&&(n=n.ownerDocument.body),n}function T0(e,t){let n=mt(e);if(Si(e))return n;if(!Ze(e)){let o=Zn(e);for(;o&&!tr(o);){if(ze(o)&&!gm(o))return o;o=Zn(o)}return n}let r=I0(e,t);for(;r&&My(r)&&gm(r);)r=I0(r,t);return r&&tr(r)&&gm(r)&&!Zc(r)?n:r||Dy(e)||n}var _E=async function(e){let t=this.getOffsetParent||T0,n=this.getDimensions,r=await n(e.floating);return{reference:PE(e.reference,await t(e.floating),e.strategy),floating:{x:0,y:0,width:r.width,height:r.height}}};function LE(e){return Xt(e).direction==="rtl"}var Pi={convertOffsetParentRelativeRectToViewportRelativeRect:yE,getDocumentElement:er,getClippingRect:RE,getOffsetParent:T0,getElementRects:_E,getClientRects:wE,getDimensions:EE,getScale:Xa,isElement:ze,isRTL:LE};function R0(e,t){return e.x===t.x&&e.y===t.y&&e.width===t.width&&e.height===t.height}function OE(e,t,n){let r=null,o,a=er(e);function l(){var d;clearTimeout(o),(d=r)==null||d.disconnect(),r=null}function i(d,p){d===void 0&&(d=!1),p===void 0&&(p=1),l();let g=e.getBoundingClientRect(),{left:m,top:b,width:h,height:y}=g;if(d||t(),!h||!y)return;let v=Ei(b),u=Ei(a.clientWidth-(m+h)),f=Ei(a.clientHeight-(b+y)),x=Ei(m),C={rootMargin:-v+"px "+-u+"px "+-f+"px "+-x+"px",threshold:Ln(0,io(1,p))||1},k=!0;function T(z){let O=z[0].intersectionRatio;if(!R0(g,e.getBoundingClientRect()))return i();if(O!==p){if(!k)return i();O?i(!1,O):o=setTimeout(()=>{i(!1,1e-7)},1e3)}k=!1}try{r=new IntersectionObserver(T,{...C,root:a.ownerDocument})}catch{r=new IntersectionObserver(T,C)}r.observe(e)}let s=mt(e),c=()=>i(n);return s.addEventListener("resize",c),i(!0),()=>{s.removeEventListener("resize",c),l()}}function du(e,t,n,r){r===void 0&&(r={});let{ancestorScroll:o=!0,ancestorResize:a=!0,elementResize:l=typeof ResizeObserver=="function",layoutShift:i=typeof IntersectionObserver=="function",animationFrame:s=!1}=r,c=hm(e),d=o||a?[...c?Qt(c):[],...t?Qt(t):[]]:[];d.forEach(v=>{o&&v.addEventListener("scroll",n),a&&v.addEventListener("resize",n)});let p=c&&i?OE(c,n,a):null,g=-1,m=null;l&&(m=new ResizeObserver(v=>{let[u]=v;u&&u.target===c&&m&&t&&(m.unobserve(t),cancelAnimationFrame(g),g=requestAnimationFrame(()=>{var f;(f=m)==null||f.observe(t)})),n()}),c&&!s&&m.observe(c),t&&m.observe(t));let b,h=s?Xo(e):null;s&&y();function y(){let v=Xo(e);h&&!R0(h,v)&&n(),h=v,b=requestAnimationFrame(y)}return n(),()=>{var v;d.forEach(u=>{o&&u.removeEventListener("scroll",n),a&&u.removeEventListener("resize",n)}),p?.(),(v=m)==null||v.disconnect(),m=null,s&&cancelAnimationFrame(b)}}var E0=h0;var P0=b0,_0=v0,L0=y0;var O0=x0,fu=(e,t,n)=>{let r=new Map,o=n??{},a={...Pi,...o.platform,_c:r};return m0(e,t,{...o,platform:a})};var tt=w(E(),1),B0=w(E(),1),A0=w(wi(),1),BE=typeof document<"u",AE=function(){},pu=BE?B0.useLayoutEffect:AE;function mu(e,t){if(e===t)return!0;if(typeof e!=typeof t)return!1;if(typeof e=="function"&&e.toString()===t.toString())return!0;let n,r,o;if(e&&t&&typeof e=="object"){if(Array.isArray(e)){if(n=e.length,n!==t.length)return!1;for(r=n;r--!==0;)if(!mu(e[r],t[r]))return!1;return!0}if(o=Object.keys(e),n=o.length,n!==Object.keys(t).length)return!1;for(r=n;r--!==0;)if(!{}.hasOwnProperty.call(t,o[r]))return!1;for(r=n;r--!==0;){let a=o[r];if(!(a==="_owner"&&e.$$typeof)&&!mu(e[a],t[a]))return!1}return!0}return e!==e&&t!==t}function F0(e){return typeof window>"u"?1:(e.ownerDocument.defaultView||window).devicePixelRatio||1}function N0(e,t){let n=F0(e);return Math.round(t*n)/n}function bm(e){let t=tt.useRef(e);return pu(()=>{t.current=e}),t}function M0(e){e===void 0&&(e={});let{placement:t="bottom",strategy:n="absolute",middleware:r=[],platform:o,elements:{reference:a,floating:l}={},transform:i=!0,whileElementsMounted:s,open:c}=e,[d,p]=tt.useState({x:0,y:0,strategy:n,placement:t,middlewareData:{},isPositioned:!1}),[g,m]=tt.useState(r);mu(g,r)||m(r);let[b,h]=tt.useState(null),[y,v]=tt.useState(null),u=tt.useCallback(_=>{_!==C.current&&(C.current=_,h(_))},[]),f=tt.useCallback(_=>{_!==k.current&&(k.current=_,v(_))},[]),x=a||b,I=l||y,C=tt.useRef(null),k=tt.useRef(null),T=tt.useRef(d),z=s!=null,O=bm(s),A=bm(o),B=bm(c),D=tt.useCallback(()=>{if(!C.current||!k.current)return;let _={placement:t,strategy:n,middleware:g};A.current&&(_.platform=A.current),fu(C.current,k.current,_).then(W=>{let ee={...W,isPositioned:B.current!==!1};N.current&&!mu(T.current,ee)&&(T.current=ee,A0.flushSync(()=>{p(ee)}))})},[g,t,n,A,B]);pu(()=>{c===!1&&T.current.isPositioned&&(T.current.isPositioned=!1,p(_=>({..._,isPositioned:!1})))},[c]);let N=tt.useRef(!1);pu(()=>(N.current=!0,()=>{N.current=!1}),[]),pu(()=>{if(x&&(C.current=x),I&&(k.current=I),x&&I){if(O.current)return O.current(x,I,D);D()}},[x,I,D,O,z]);let R=tt.useMemo(()=>({reference:C,floating:k,setReference:u,setFloating:f}),[u,f]),P=tt.useMemo(()=>({reference:x,floating:I}),[x,I]),j=tt.useMemo(()=>{let _={position:n,left:0,top:0};if(!P.floating)return _;let W=N0(P.floating,d.x),ee=N0(P.floating,d.y);return i?{..._,transform:"translate("+W+"px, "+ee+"px)",...F0(P.floating)>=1.5&&{willChange:"transform"}}:{position:n,left:W,top:ee}},[n,i,P.floating,d.x,d.y]);return tt.useMemo(()=>({...d,update:D,refs:R,elements:P,floatingStyles:j}),[d,D,R,P,j])}var uo=(e,t)=>{let n=E0(e);return{name:n.name,fn:n.fn,options:[e,t]}},_i=(e,t)=>{let n=P0(e);return{name:n.name,fn:n.fn,options:[e,t]}},xm=(e,t)=>({fn:O0(e).fn,options:[e,t]}),kr=(e,t)=>{let n=_0(e);return{name:n.name,fn:n.fn,options:[e,t]}},Zo=(e,t)=>{let n=L0(e);return{name:n.name,fn:n.fn,options:[e,t]}};var FE="data-floating-ui-focusable",D0="active",z0="selected",ME="ArrowLeft",DE="ArrowRight",zE="ArrowUp",WE="ArrowDown";var jE=[ME,DE],VE=[zE,WE],nO=[...jE,...VE];var HE={...q},W0=!1,$E=0,j0=()=>"floating-ui-"+Math.random().toString(36).slice(2,6)+$E++;function UE(){let[e,t]=q.useState(()=>W0?j0():void 0);return Jt(()=>{e==null&&t(j0())},[]),q.useEffect(()=>{W0=!0},[]),e}var KE=HE.useId,J0=KE||UE;function GE(){let e=new Map;return{emit(t,n){var r;(r=e.get(t))==null||r.forEach(o=>o(n))},on(t,n){e.has(t)||e.set(t,new Set),e.get(t).add(n)},off(t,n){var r;(r=e.get(t))==null||r.delete(n)}}}var qE=q.createContext(null),YE=q.createContext(null),QE=()=>{var e;return((e=q.useContext(qE))==null?void 0:e.id)||null},Sm=()=>q.useContext(YE);function el(e){return"data-floating-ui-"+e}function ew(e){e.current!==-1&&(clearTimeout(e.current),e.current=-1)}var V0=0;function Za(e,t){t===void 0&&(t={});let{preventScroll:n=!1,cancelPrevious:r=!0,sync:o=!1}=t;r&&cancelAnimationFrame(V0);let a=()=>e?.focus({preventScroll:n});o?a():V0=requestAnimationFrame(a)}function XE(e){return e?.ownerDocument||document}var Ja={inert:new WeakMap,"aria-hidden":new WeakMap,none:new WeakMap};function H0(e){return e==="inert"?Ja.inert:e==="aria-hidden"?Ja["aria-hidden"]:Ja.none}var vu=new WeakSet,gu={},ym=0,ZE=()=>typeof HTMLElement<"u"&&"inert"in HTMLElement.prototype;function tw(e){return e?$a(e)?e.host:tw(e.parentNode):null}var JE=(e,t)=>t.map(n=>{if(e.contains(n))return n;let r=tw(n);return e.contains(r)?r:null}).filter(n=>n!=null);function eP(e,t,n,r){let o="data-floating-ui-inert",a=r?"inert":n?"aria-hidden":null,l=JE(t,e),i=new Set,s=new Set(l),c=[];gu[o]||(gu[o]=new WeakMap);let d=gu[o];l.forEach(p),g(t),i.clear();function p(m){!m||i.has(m)||(i.add(m),m.parentNode&&p(m.parentNode))}function g(m){!m||s.has(m)||[].forEach.call(m.children,b=>{if(Jn(b)!=="script")if(i.has(b))g(b);else{let h=a?b.getAttribute(a):null,y=h!==null&&h!=="false",v=H0(a),u=(v.get(b)||0)+1,f=(d.get(b)||0)+1;v.set(b,u),d.set(b,f),c.push(b),u===1&&y&&vu.add(b),f===1&&b.setAttribute(o,""),!y&&a&&b.setAttribute(a,a==="inert"?"":"true")}})}return ym++,()=>{c.forEach(m=>{let b=H0(a),y=(b.get(m)||0)-1,v=(d.get(m)||0)-1;b.set(m,y),d.set(m,v),y||(!vu.has(m)&&a&&m.removeAttribute(a),vu.delete(m)),v||m.removeAttribute(o)}),ym--,ym||(Ja.inert=new WeakMap,Ja["aria-hidden"]=new WeakMap,Ja.none=new WeakMap,vu=new WeakSet,gu={})}}function $0(e,t,n){t===void 0&&(t=!1),n===void 0&&(n=!1);let r=XE(e[0]).body;return eP(e.concat(Array.from(r.querySelectorAll('[aria-live],[role="status"],output'))),r,t,n)}var km={border:0,clip:"rect(0 0 0 0)",height:"1px",margin:"-1px",overflow:"hidden",padding:0,position:"fixed",whiteSpace:"nowrap",width:"1px",top:0,left:0},hu=q.forwardRef(function(t,n){let[r,o]=q.useState();Jt(()=>{sm()&&o("button")},[]);let a={ref:n,tabIndex:0,role:r,"aria-hidden":r?void 0:!0,[el("focus-guard")]:"",style:km};return(0,Vt.jsx)("span",{...t,...a})}),tP={clipPath:"inset(50%)",position:"fixed",top:0,left:0},nw=q.createContext(null),U0=el("portal");function nP(e){e===void 0&&(e={});let{id:t,root:n}=e,r=J0(),o=rw(),[a,l]=q.useState(null),i=q.useRef(null);return Jt(()=>()=>{a?.remove(),queueMicrotask(()=>{i.current=null})},[a]),Jt(()=>{if(!r||i.current)return;let s=t?document.getElementById(t):null;if(!s)return;let c=document.createElement("div");c.id=r,c.setAttribute(U0,""),s.appendChild(c),i.current=c,l(c)},[t,r]),Jt(()=>{if(n===null||!r||i.current)return;let s=n||o?.portalNode;s&&!Xc(s)&&(s=s.current),s=s||document.body;let c=null;t&&(c=document.createElement("div"),c.id=t,s.appendChild(c));let d=document.createElement("div");d.id=r,d.setAttribute(U0,""),s=c||s,s.appendChild(d),i.current=d,l(d)},[t,n,r,o]),a}function Tm(e){let{children:t,id:n,root:r,preserveTabOrder:o=!0}=e,a=nP({id:n,root:r}),[l,i]=q.useState(null),s=q.useRef(null),c=q.useRef(null),d=q.useRef(null),p=q.useRef(null),g=l?.modal,m=l?.open,b=!!l&&!l.modal&&l.open&&o&&!!(r||a);return q.useEffect(()=>{if(!a||!o||g)return;function h(y){a&&Qa(y)&&(y.type==="focusin"?vm:d0)(a)}return a.addEventListener("focusin",h,!0),a.addEventListener("focusout",h,!0),()=>{a.removeEventListener("focusin",h,!0),a.removeEventListener("focusout",h,!0)}},[a,o,g]),q.useEffect(()=>{a&&(m||vm(a))},[m,a]),(0,Vt.jsxs)(nw.Provider,{value:q.useMemo(()=>({preserveTabOrder:o,beforeOutsideRef:s,afterOutsideRef:c,beforeInsideRef:d,afterInsideRef:p,portalNode:a,setFocusManagerState:i}),[o,a]),children:[b&&a&&(0,Vt.jsx)(hu,{"data-type":"outside",ref:s,onFocus:h=>{if(Qa(h,a)){var y;(y=d.current)==null||y.focus()}else{let v=l?l.domReference:null,u=mm(v);u?.focus()}}}),b&&a&&(0,Vt.jsx)("span",{"aria-owns":a.id,style:tP}),a&&Cm.createPortal(t,a),b&&a&&(0,Vt.jsx)(hu,{"data-type":"outside",ref:c,onFocus:h=>{if(Qa(h,a)){var y;(y=p.current)==null||y.focus()}else{let v=l?l.domReference:null,u=pm(v);u?.focus(),l?.closeOnFocusOut&&l?.onOpenChange(!1,h.nativeEvent,"focus-out")}}})]})}var rw=()=>q.useContext(nw);function K0(e){return q.useMemo(()=>t=>{e.forEach(n=>{n&&(n.current=t)})},e)}var G0=20,fo=[];function Rm(){fo=fo.filter(e=>{var t;return(t=e.deref())==null?void 0:t.isConnected})}function rP(e){Rm(),e&&Jn(e)!=="body"&&(fo.push(new WeakRef(e)),fo.length>G0&&(fo=fo.slice(-G0)))}function q0(){Rm();let e=fo[fo.length-1];return e?.deref()}function oP(e){let t=Ya();return om(e,t)?e:co(e,t)[0]||e}function Y0(e,t){var n;if(!t.current.includes("floating")&&!((n=e.getAttribute("role"))!=null&&n.includes("dialog")))return;let r=Ya(),a=e0(e,r).filter(i=>{let s=i.getAttribute("data-tabindex")||"";return om(i,r)||i.hasAttribute("data-tabindex")&&!s.startsWith("-")}),l=e.getAttribute("tabindex");t.current.includes("floating")||a.length===0?l!=="0"&&e.setAttribute("tabindex","0"):(l!=="-1"||e.hasAttribute("data-tabindex")&&e.getAttribute("data-tabindex")!=="-1")&&(e.setAttribute("tabindex","-1"),e.setAttribute("data-tabindex","-1"))}var aP=q.forwardRef(function(t,n){return(0,Vt.jsx)("button",{...t,type:"button",ref:n,tabIndex:-1,style:km})});function ow(e){let{context:t,children:n,disabled:r=!1,order:o=["content"],guards:a=!0,initialFocus:l=0,returnFocus:i=!0,restoreFocus:s=!1,modal:c=!0,visuallyHiddenDismiss:d=!1,closeOnFocusOut:p=!0,outsideElementsInert:g=!1,getInsideElements:m=()=>[]}=e,{open:b,onOpenChange:h,events:y,dataRef:v,elements:{domReference:u,floating:f}}=t,x=Nn(()=>{var $;return($=v.current.floatingContext)==null?void 0:$.nodeId}),I=Nn(m),C=typeof l=="number"&&l<0,k=cm(u)&&C,T=ZE(),z=T?a:!0,O=!z||T&&g,A=cu(o),B=cu(l),D=cu(i),N=Sm(),R=rw(),P=q.useRef(null),j=q.useRef(null),_=q.useRef(!1),W=q.useRef(!1),ee=q.useRef(-1),ne=q.useRef(-1),de=R!=null,U=um(f),me=Nn(function($){return $===void 0&&($=U),$?co($,Ya()):[]}),ce=Nn($=>{let M=me($);return A.current.map(X=>u&&X==="reference"?u:U&&X==="floating"?U:M).filter(Boolean).flat()});q.useEffect(()=>{if(r||!c)return;function $(X){if(X.key==="Tab"){It(U,Sr(Zt(U)))&&me().length===0&&!k&&su(X);let he=ce(),Se=rr(X);A.current[0]==="reference"&&Se===u&&(su(X),X.shiftKey?Za(he[he.length-1]):Za(he[1])),A.current[1]==="floating"&&Se===U&&X.shiftKey&&(su(X),Za(he[0]))}}let M=Zt(U);return M.addEventListener("keydown",$),()=>{M.removeEventListener("keydown",$)}},[r,u,U,c,A,k,me,ce]),q.useEffect(()=>{if(r||!f)return;function $(M){let X=rr(M),Se=me().indexOf(X);Se!==-1&&(ee.current=Se)}return f.addEventListener("focusin",$),()=>{f.removeEventListener("focusin",$)}},[r,f,me]),q.useEffect(()=>{if(r||!p)return;function $(){W.current=!0,setTimeout(()=>{W.current=!1})}function M(Se){let ge=Se.relatedTarget,ve=Se.currentTarget,we=rr(Se);queueMicrotask(()=>{let ye=x(),_e=!(It(u,ge)||It(f,ge)||It(ge,f)||It(R?.portalNode,ge)||ge!=null&&ge.hasAttribute(el("focus-guard"))||N&&(Qo(N.nodesRef.current,ye).find(L=>{var K,oe;return It((K=L.context)==null?void 0:K.elements.floating,ge)||It((oe=L.context)==null?void 0:oe.elements.domReference,ge)})||dm(N.nodesRef.current,ye).find(L=>{var K,oe,pe;return[(K=L.context)==null?void 0:K.elements.floating,um((oe=L.context)==null?void 0:oe.elements.floating)].includes(ge)||((pe=L.context)==null?void 0:pe.elements.domReference)===ge})));if(ve===u&&U&&Y0(U,A),s&&ve!==u&&!(we!=null&&we.isConnected)&&Sr(Zt(U))===Zt(U).body){Ze(U)&&U.focus();let L=ee.current,K=me(),oe=K[L]||K[K.length-1]||U;Ze(oe)&&oe.focus()}if(v.current.insideReactTree){v.current.insideReactTree=!1;return}(k||!c)&&ge&&_e&&!W.current&&ge!==q0()&&(_.current=!0,h(!1,Se,"focus-out"))})}let X=!!(!N&&R);function he(){ew(ne),v.current.insideReactTree=!0,ne.current=window.setTimeout(()=>{v.current.insideReactTree=!1})}if(f&&Ze(u))return u.addEventListener("focusout",M),u.addEventListener("pointerdown",$),f.addEventListener("focusout",M),X&&f.addEventListener("focusout",he,!0),()=>{u.removeEventListener("focusout",M),u.removeEventListener("pointerdown",$),f.removeEventListener("focusout",M),X&&f.removeEventListener("focusout",he,!0)}},[r,u,f,U,c,N,R,h,p,s,me,k,x,A,v]);let be=q.useRef(null),fe=q.useRef(null),re=K0([be,R?.beforeInsideRef]),G=K0([fe,R?.afterInsideRef]);q.useEffect(()=>{var $,M;if(r||!f)return;let X=Array.from((R==null||($=R.portalNode)==null?void 0:$.querySelectorAll("["+el("portal")+"]"))||[]),Se=(M=(N?dm(N.nodesRef.current,x()):[]).find(we=>{var ye;return cm(((ye=we.context)==null?void 0:ye.elements.domReference)||null)}))==null||(M=M.context)==null?void 0:M.elements.domReference,ge=[f,Se,...X,...I(),P.current,j.current,be.current,fe.current,R?.beforeOutsideRef.current,R?.afterOutsideRef.current,A.current.includes("reference")||k?u:null].filter(we=>we!=null),ve=c||k?$0(ge,!O,O):$0(ge);return()=>{ve()}},[r,u,f,c,A,R,k,z,O,N,x,I]),Jt(()=>{if(r||!Ze(U))return;let $=Zt(U),M=Sr($);queueMicrotask(()=>{let X=ce(U),he=B.current,Se=(typeof he=="number"?X[he]:he.current)||U,ge=It(U,M);!C&&!ge&&b&&Za(Se,{preventScroll:Se===U})})},[r,b,U,C,ce,B]),Jt(()=>{if(r||!U)return;let $=Zt(U),M=Sr($);rP(M);function X(ge){let{reason:ve,event:we,nested:ye}=ge;if(["hover","safe-polygon"].includes(ve)&&we.type==="mouseleave"&&(_.current=!0),ve==="outside-press")if(ye)_.current=!1;else if(s0(we)||c0(we))_.current=!1;else{let _e=!1;document.createElement("div").focus({get preventScroll(){return _e=!0,!1}}),_e?_.current=!1:_.current=!0}}y.on("openchange",X);let he=$.createElement("span");he.setAttribute("tabindex","-1"),he.setAttribute("aria-hidden","true"),Object.assign(he.style,km),de&&u&&u.insertAdjacentElement("afterend",he);function Se(){if(typeof D.current=="boolean"){let ge=u||q0();return ge&&ge.isConnected?ge:he}return D.current.current||he}return()=>{y.off("openchange",X);let ge=Sr($),ve=It(f,ge)||N&&Qo(N.nodesRef.current,x(),!1).some(ye=>{var _e;return It((_e=ye.context)==null?void 0:_e.elements.floating,ge)}),we=Se();queueMicrotask(()=>{let ye=oP(we);D.current&&!_.current&&Ze(ye)&&(!(ye!==ge&&ge!==$.body)||ve)&&ye.focus({preventScroll:!0}),he.remove()})}},[r,f,U,D,v,y,N,de,u,x]),q.useEffect(()=>(queueMicrotask(()=>{_.current=!1}),()=>{queueMicrotask(Rm)}),[r]),Jt(()=>{if(!r&&R)return R.setFocusManagerState({modal:c,closeOnFocusOut:p,open:b,onOpenChange:h,domReference:u}),()=>{R.setFocusManagerState(null)}},[r,R,c,b,h,p,u]),Jt(()=>{r||U&&Y0(U,A)},[r,U,A]);function Z($){return r||!d||!c?null:(0,Vt.jsx)(aP,{ref:$==="start"?P:j,onClick:M=>h(!1,M.nativeEvent),children:typeof d=="string"?d:"Dismiss"})}let se=!r&&z&&(c?!k:!0)&&(de||c);return(0,Vt.jsxs)(Vt.Fragment,{children:[se&&(0,Vt.jsx)(hu,{"data-type":"inside",ref:re,onFocus:$=>{if(c){let X=ce();Za(o[0]==="reference"?X[0]:X[X.length-1])}else if(R!=null&&R.preserveTabOrder&&R.portalNode)if(_.current=!1,Qa($,R.portalNode)){let X=pm(u);X?.focus()}else{var M;(M=R.beforeOutsideRef.current)==null||M.focus()}}}),!k&&Z("start"),n,Z("end"),se&&(0,Vt.jsx)(hu,{"data-type":"inside",ref:G,onFocus:$=>{if(c)Za(ce()[0]);else if(R!=null&&R.preserveTabOrder&&R.portalNode)if(p&&(_.current=!0),Qa($,R.portalNode)){let X=mm(u);X?.focus()}else{var M;(M=R.afterOutsideRef.current)==null||M.focus()}}})]})}function Q0(e){return Ze(e.target)&&e.target.tagName==="BUTTON"}function lP(e){return Ze(e.target)&&e.target.tagName==="A"}function X0(e){return iu(e)}function tl(e,t){t===void 0&&(t={});let{open:n,onOpenChange:r,dataRef:o,elements:{domReference:a}}=e,{enabled:l=!0,event:i="click",toggle:s=!0,ignoreMouse:c=!1,keyboardHandlers:d=!0,stickIfOpen:p=!0}=t,g=q.useRef(),m=q.useRef(!1),b=q.useMemo(()=>({onPointerDown(h){g.current=h.pointerType},onMouseDown(h){let y=g.current;h.button===0&&i!=="click"&&(fm(y,!0)&&c||(n&&s&&(!(o.current.openEvent&&p)||o.current.openEvent.type==="mousedown")?r(!1,h.nativeEvent,"click"):(h.preventDefault(),r(!0,h.nativeEvent,"click"))))},onClick(h){let y=g.current;if(i==="mousedown"&&g.current){g.current=void 0;return}fm(y,!0)&&c||(n&&s&&(!(o.current.openEvent&&p)||o.current.openEvent.type==="click")?r(!1,h.nativeEvent,"click"):r(!0,h.nativeEvent,"click"))},onKeyDown(h){g.current=void 0,!(h.defaultPrevented||!d||Q0(h))&&(h.key===" "&&!X0(a)&&(h.preventDefault(),m.current=!0),!lP(h)&&h.key==="Enter"&&r(!(n&&s),h.nativeEvent,"click"))},onKeyUp(h){h.defaultPrevented||!d||Q0(h)||X0(a)||h.key===" "&&m.current&&(m.current=!1,r(!(n&&s),h.nativeEvent,"click"))}}),[o,a,i,c,d,r,n,p,s]);return q.useMemo(()=>l?{reference:b}:{},[l,b])}var iP={pointerdown:"onPointerDown",mousedown:"onMouseDown",click:"onClick"},sP={pointerdown:"onPointerDownCapture",mousedown:"onMouseDownCapture",click:"onClickCapture"},Z0=e=>{var t,n;return{escapeKey:typeof e=="boolean"?e:(t=e?.escapeKey)!=null?t:!1,outsidePress:typeof e=="boolean"?e:(n=e?.outsidePress)!=null?n:!0}};function nl(e,t){t===void 0&&(t={});let{open:n,onOpenChange:r,elements:o,dataRef:a}=e,{enabled:l=!0,escapeKey:i=!0,outsidePress:s=!0,outsidePressEvent:c="pointerdown",referencePress:d=!1,referencePressEvent:p="pointerdown",ancestorScroll:g=!1,bubbles:m,capture:b}=t,h=Sm(),y=Nn(typeof s=="function"?s:()=>!1),v=typeof s=="function"?y:s,u=q.useRef(!1),{escapeKey:f,outsidePress:x}=Z0(m),{escapeKey:I,outsidePress:C}=Z0(b),k=q.useRef(!1),T=Nn(N=>{var R;if(!n||!l||!i||N.key!=="Escape"||k.current)return;let P=(R=a.current.floatingContext)==null?void 0:R.nodeId,j=h?Qo(h.nodesRef.current,P):[];if(!f&&(N.stopPropagation(),j.length>0)){let _=!0;if(j.forEach(W=>{var ee;if((ee=W.context)!=null&&ee.open&&!W.context.dataRef.current.__escapeKeyBubbles){_=!1;return}}),!_)return}r(!1,i0(N)?N.nativeEvent:N,"escape-key")}),z=Nn(N=>{var R;let P=()=>{var j;T(N),(j=rr(N))==null||j.removeEventListener("keydown",P)};(R=rr(N))==null||R.addEventListener("keydown",P)}),O=Nn(N=>{var R;let P=a.current.insideReactTree;a.current.insideReactTree=!1;let j=u.current;if(u.current=!1,c==="click"&&j||P||typeof v=="function"&&!v(N))return;let _=rr(N),W="["+el("inert")+"]",ee=Zt(o.floating).querySelectorAll(W),ne=ze(_)?_:null;for(;ne&&!tr(ne);){let ce=Zn(ne);if(tr(ce)||!ze(ce))break;ne=ce}if(ee.length&&ze(_)&&!a0(_)&&!It(_,o.floating)&&Array.from(ee).every(ce=>!It(ne,ce)))return;if(Ze(_)&&D){let ce=tr(_),be=Xt(_),fe=/auto|scroll/,re=ce||fe.test(be.overflowX),G=ce||fe.test(be.overflowY),Z=re&&_.clientWidth>0&&_.scrollWidth>_.clientWidth,se=G&&_.clientHeight>0&&_.scrollHeight>_.clientHeight,$=be.direction==="rtl",M=se&&($?N.offsetX<=_.offsetWidth-_.clientWidth:N.offsetX>_.clientWidth),X=Z&&N.offsetY>_.clientHeight;if(M||X)return}let de=(R=a.current.floatingContext)==null?void 0:R.nodeId,U=h&&Qo(h.nodesRef.current,de).some(ce=>{var be;return lu(N,(be=ce.context)==null?void 0:be.elements.floating)});if(lu(N,o.floating)||lu(N,o.domReference)||U)return;let me=h?Qo(h.nodesRef.current,de):[];if(me.length>0){let ce=!0;if(me.forEach(be=>{var fe;if((fe=be.context)!=null&&fe.open&&!be.context.dataRef.current.__outsidePressBubbles){ce=!1;return}}),!ce)return}r(!1,N,"outside-press")}),A=Nn(N=>{var R;let P=()=>{var j;O(N),(j=rr(N))==null||j.removeEventListener(c,P)};(R=rr(N))==null||R.addEventListener(c,P)});q.useEffect(()=>{if(!n||!l)return;a.current.__escapeKeyBubbles=f,a.current.__outsidePressBubbles=x;let N=-1;function R(ee){r(!1,ee,"ancestor-scroll")}function P(){window.clearTimeout(N),k.current=!0}function j(){N=window.setTimeout(()=>{k.current=!1},Ua()?5:0)}let _=Zt(o.floating);i&&(_.addEventListener("keydown",I?z:T,I),_.addEventListener("compositionstart",P),_.addEventListener("compositionend",j)),v&&_.addEventListener(c,C?A:O,C);let W=[];return g&&(ze(o.domReference)&&(W=Qt(o.domReference)),ze(o.floating)&&(W=W.concat(Qt(o.floating))),!ze(o.reference)&&o.reference&&o.reference.contextElement&&(W=W.concat(Qt(o.reference.contextElement)))),W=W.filter(ee=>{var ne;return ee!==((ne=_.defaultView)==null?void 0:ne.visualViewport)}),W.forEach(ee=>{ee.addEventListener("scroll",R)}),()=>{i&&(_.removeEventListener("keydown",I?z:T,I),_.removeEventListener("compositionstart",P),_.removeEventListener("compositionend",j)),v&&_.removeEventListener(c,C?A:O,C),W.forEach(ee=>{ee.removeEventListener("scroll",R)}),window.clearTimeout(N)}},[a,o,i,v,c,n,r,g,l,f,x,T,I,z,O,C,A]),q.useEffect(()=>{a.current.insideReactTree=!1},[a,v,c]);let B=q.useMemo(()=>({onKeyDown:T,...d&&{[iP[p]]:N=>{r(!1,N.nativeEvent,"reference-press")},...p!=="click"&&{onClick(N){r(!1,N.nativeEvent,"reference-press")}}}}),[T,r,d,p]),D=q.useMemo(()=>{function N(R){R.button===0&&(u.current=!0)}return{onKeyDown:T,onMouseDown:N,onMouseUp:N,[sP[c]]:()=>{a.current.insideReactTree=!0}}},[T,c,a]);return q.useMemo(()=>l?{reference:B,floating:D}:{},[l,B,D])}function cP(e){let{open:t=!1,onOpenChange:n,elements:r}=e,o=J0(),a=q.useRef({}),[l]=q.useState(()=>GE()),i=QE()!=null,[s,c]=q.useState(r.reference),d=Nn((m,b,h)=>{a.current.openEvent=m?b:void 0,l.emit("openchange",{open:m,event:b,reason:h,nested:i}),n?.(m,b,h)}),p=q.useMemo(()=>({setPositionReference:c}),[]),g=q.useMemo(()=>({reference:s||r.reference||null,floating:r.floating||null,domReference:r.reference}),[s,r.reference,r.floating]);return q.useMemo(()=>({dataRef:a,open:t,onOpenChange:d,elements:g,events:l,floatingId:o,refs:p}),[t,d,g,l,o,p])}function aw(e){var t,n;let{elements:r,...o}=e===void 0?{}:e,{nodeId:a}=o,l=cP({...o,elements:{reference:(t=r?.reference)!=null?t:null,floating:(n=r?.floating)!=null?n:null}}),i=o.rootContext||l,s=i.elements,[c,d]=q.useState(null),[p,g]=q.useState(null),b=s?.domReference||c,h=q.useRef(null),y=Sm();Jt(()=>{b&&(h.current=b)},[b]);let v=M0({...o,elements:{...s,...p&&{reference:p}}}),u=q.useCallback(k=>{let T=ze(k)?{getBoundingClientRect:()=>k.getBoundingClientRect(),getClientRects:()=>k.getClientRects(),contextElement:k}:k;g(T),v.refs.setReference(T)},[v.refs]),f=q.useCallback(k=>{(ze(k)||k===null)&&(h.current=k,d(k)),(ze(v.refs.reference.current)||v.refs.reference.current===null||k!==null&&!ze(k))&&v.refs.setReference(k)},[v.refs]),x=q.useMemo(()=>({...v.refs,setReference:f,setPositionReference:u,domReference:h}),[v.refs,f,u]),I=q.useMemo(()=>({...v.elements,domReference:b}),[v.elements,b]),C=q.useMemo(()=>({...v,...i,refs:x,elements:I,nodeId:a}),[v,x,I,a,i]);return Jt(()=>{i.dataRef.current.floatingContext=C;let k=y?.nodesRef.current.find(T=>T.id===a);k&&(k.context=C)}),q.useMemo(()=>({...v,context:C,refs:x,elements:I}),[v,x,I,C])}function wm(){return r0()&&sm()}function bu(e,t){t===void 0&&(t={});let{open:n,onOpenChange:r,events:o,dataRef:a,elements:l}=e,{enabled:i=!0,visibleOnly:s=!0}=t,c=q.useRef(!1),d=q.useRef(-1),p=q.useRef(!0);q.useEffect(()=>{if(!i)return;let m=mt(l.domReference);function b(){!n&&Ze(l.domReference)&&l.domReference===Sr(Zt(l.domReference))&&(c.current=!0)}function h(){p.current=!0}function y(){p.current=!1}return m.addEventListener("blur",b),wm()&&(m.addEventListener("keydown",h,!0),m.addEventListener("pointerdown",y,!0)),()=>{m.removeEventListener("blur",b),wm()&&(m.removeEventListener("keydown",h,!0),m.removeEventListener("pointerdown",y,!0))}},[l.domReference,n,i]),q.useEffect(()=>{if(!i)return;function m(b){let{reason:h}=b;(h==="reference-press"||h==="escape-key")&&(c.current=!0)}return o.on("openchange",m),()=>{o.off("openchange",m)}},[o,i]),q.useEffect(()=>()=>{ew(d)},[]);let g=q.useMemo(()=>({onMouseLeave(){c.current=!1},onFocus(m){if(c.current)return;let b=rr(m.nativeEvent);if(s&&ze(b)){if(wm()&&!m.relatedTarget){if(!p.current&&!iu(b))return}else if(!l0(b))return}r(!0,m.nativeEvent,"focus")},onBlur(m){c.current=!1;let b=m.relatedTarget,h=m.nativeEvent,y=ze(b)&&b.hasAttribute(el("focus-guard"))&&b.getAttribute("data-type")==="outside";d.current=window.setTimeout(()=>{var v;let u=Sr(l.domReference?l.domReference.ownerDocument:document);!b&&u===l.domReference||It((v=a.current.floatingContext)==null?void 0:v.refs.floating.current,u)||It(l.domReference,u)||y||r(!1,h,"focus")})}}),[a,l.domReference,r,s]);return q.useMemo(()=>i?{reference:g}:{},[i,g])}function Im(e,t,n){let r=new Map,o=n==="item",a=e;if(o&&e){let{[D0]:l,[z0]:i,...s}=e;a=s}return{...n==="floating"&&{tabIndex:-1,[FE]:""},...a,...t.map(l=>{let i=l?l[n]:null;return typeof i=="function"?e?i(e):null:i}).concat(e).reduce((l,i)=>(i&&Object.entries(i).forEach(s=>{let[c,d]=s;if(!(o&&[D0,z0].includes(c)))if(c.indexOf("on")===0){if(r.has(c)||r.set(c,[]),typeof d=="function"){var p;(p=r.get(c))==null||p.push(d),l[c]=function(){for(var g,m=arguments.length,b=new Array(m),h=0;h<m;h++)b[h]=arguments[h];return(g=r.get(c))==null?void 0:g.map(y=>y(...b)).find(y=>y!==void 0)}}}else l[c]=d}),l),{})}}function rl(e){e===void 0&&(e=[]);let t=e.map(i=>i?.reference),n=e.map(i=>i?.floating),r=e.map(i=>i?.item),o=q.useCallback(i=>Im(i,e,"reference"),t),a=q.useCallback(i=>Im(i,e,"floating"),n),l=q.useCallback(i=>Im(i,e,"item"),r);return q.useMemo(()=>({getReferenceProps:o,getFloatingProps:a,getItemProps:l}),[o,a,l])}var Rr=w(E());var en=w(F());var Bn=w(E());var Jo=w(E()),lw=Jo.useId,uP=BigInt(0);function dP(e){let[t,n]=Jo.useState(e),r=e||t;return Jo.useEffect(()=>{t==null&&n(`salt-${++uP}`)},[t]),r}function We(e){if(lw!==void 0){let t=lw();return e??t}return dP(e)}var sw=w(F()),ol=w(E());var xu=w(E()),ie=typeof window<"u"&&typeof window.document<"u"&&typeof window.document.createElement<"u"?xu.useLayoutEffect:xu.useEffect;var iw=(0,ol.createContext)(null),cw=({children:e})=>{let t=(0,ol.useContext)(iw),[n,r]=(0,ol.useState)(t),o=t===null,a=t||n||0;return ie(()=>{let l=null;return o&&(l=new ResizeObserver(i=>{r(i[0].contentRect.width)}),l.observe(document.body),r(document.body.getBoundingClientRect().width)),()=>{l&&l.disconnect()}},[o]),(0,sw.jsx)(iw.Provider,{value:a,children:e})};var uw=w(E()),yu=(0,uw.createContext)(void 0);var Tr=w(F());var it=w(E());var al=new Map;function dw(e,t){let n=al.get(e)??[];return n.push(t),al.set(e,n),()=>{let r=al.get(e);if(!r)return;let o=r.lastIndexOf(t);o!==-1&&r.splice(o,1),r.length===0?al.delete(e):al.set(e,r)}}function fw(e){let t=al.get(e);return t?.[t.length-1]}var pw=300,mw=(0,it.forwardRef)(function(t,n){return(0,Tr.jsx)("div",{"aria-atomic":!1,ref:n,...t})}),vw=(0,it.forwardRef)(function({children:t,style:n,target:r,...o},a){let l=Y(),[i,s]=(0,it.useState)([]),[c,d]=(0,it.useState)([]),p=(0,it.useRef)(0),g=(0,it.useRef)(!0),m=(0,it.useRef)(new Set),b=(0,it.useCallback)((u,f,x)=>{if(!l)return;let I=f==="polite"?s:d,C=l.setTimeout(()=>{m.current.delete(C),I(k=>k.filter(T=>T.id!==u))},x);m.current.add(C)},[l]),h=(0,it.useCallback)((u,f="polite",x=pw)=>{if(!g.current)return;p.current+=1;let I=`announce-${f}-${Date.now()}-${p.current}`;f==="polite"?s(C=>C.concat({id:I,message:u})):d(C=>C.concat({id:I,message:u})),b(I,f,x)},[b]);(0,it.useEffect)(()=>(g.current=!0,()=>{g.current=!1}),[]),(0,it.useEffect)(()=>{let u=m.current;return()=>{for(let f of u)l?.clearTimeout(f);u.clear()}},[l]);let y=(0,it.useCallback)((u,f={})=>{let x=typeof f=="object"&&f?f:{};h(u,x.ariaLive,x.duration??pw)},[h]),v=(0,it.useMemo)(()=>({announce:y}),[y]);return ie(()=>{if(r)return dw(r,y)},[y,r]),(0,Tr.jsxs)(yu.Provider,{value:v,children:[t,(0,Tr.jsxs)("div",{style:{position:"absolute",height:1,width:1,padding:0,margin:-1,overflow:"hidden",clip:"rect(0, 0, 0, 0)",whiteSpace:"nowrap",borderWidth:0,...n},...o,ref:a,children:[(0,Tr.jsx)(mw,{"aria-live":"polite",children:i.map(u=>(0,Tr.jsx)("div",{children:u.message},`polite-${u.id}`))}),(0,Tr.jsx)(mw,{"aria-live":"assertive",children:c.map(u=>(0,Tr.jsx)("div",{children:u.message},`assertive-${u.id}`))})]})]})});var hw=w(F()),ll=w(E());var gw=w(E());function je(e,t){return(0,gw.createContext)(t)}var bw=je("BreakpointContext",{matchedBreakpoints:[]});function xw(e){let{children:t,matchedBreakpoints:n}=e;return(0,hw.jsx)(bw.Provider,{value:{matchedBreakpoints:n},children:t})}function yw(e){let t=(0,ll.useMemo)(()=>Object.entries(e).sort(([,a],[,l])=>l-a),[e]),n=typeof window<"u"&&typeof window.matchMedia=="function",[r,o]=(0,ll.useState)(Object.fromEntries(t.map(([a])=>[a,!1])));return ie(()=>{if(!n)return;let l=t.map(([,i])=>`(min-width: ${i}px)`).map((i,s)=>{let c=window.matchMedia(i),d=t[s][0];return{mq:c,handler:()=>{o(p=>({...p,[d]:c.matches}))}}});for(let{mq:i,handler:s}of l)s(),i.addEventListener("change",s);return()=>{for(let{mq:i,handler:s}of l)i.removeEventListener("change",s)}},[n,t]),Object.keys(r).filter(a=>r[a])}function wu(){let{matchedBreakpoints:e}=(0,ll.useContext)(bw);return{matchedBreakpoints:e,breakpoint:e[0]??null}}var Em={xs:0,sm:600,md:960,lg:1280,xl:1920};var Pm=je("ProviderContext",null);var ww=`.salt-provider {
  display: contents;
}
`;var Iw=w(F());var Cu=w(E());var Iu=Symbol.for("salt-provider");function Cw({applyClassesTo:e,children:t,density:n,mode:r,theme:o,corner:a,headingFont:l,accent:i,actionFont:s}){var c;let d=Y(),p=We();ie(()=>{if(e!=="root"||!d||!p)return;let m=d.document;if(m[Iu]||(m[Iu]=p),p!==m[Iu]){console.warn("Multiple providers targeting the same window. There can be only one level root level SaltProvider per window.");return}let b=o.split(" ");return m.documentElement.classList.add(...b,`salt-density-${n}`),m.documentElement.dataset.mode=r,a&&(m.documentElement.dataset.corner=a),l&&(m.documentElement.dataset.headingFont=l),i&&(m.documentElement.dataset.accent=i),s&&(m.documentElement.dataset.actionFont=s),()=>{delete m[Iu],m.documentElement.classList.remove(...b,`salt-density-${n}`),m.documentElement.dataset.mode=void 0,delete m.documentElement.dataset.corner,delete m.documentElement.dataset.headingFont,delete m.documentElement.dataset.accent,delete m.documentElement.dataset.actionFont}},[p,e,n,r,o,d,a,l,i,s]);let g={"data-corner":a,"data-heading-font":l,"data-accent":i,"data-action-font":s};return e==="child"?(0,Cu.isValidElement)(t)?(0,Cu.cloneElement)(t,{className:V((c=t.props)==null?void 0:c.className,o,`salt-density-${n}`),"data-mode":r,...g}):(console.warn(`
SaltProvider can only apply CSS classes for theming to a single nested child element of the SaltProvider.
        Either wrap elements with a single container or consider removing the applyClassesToChild prop, in which case a
        div element will wrap your child elements`),t):e==="scope"?(0,Iw.jsx)("div",{className:V("salt-provider",o,`salt-density-${n}`),"data-mode":r,...g,children:t}):t}var Am="medium",Sw="salt-theme",fP="salt-theme-next",pP="light",_m="sharp",Lm="Open Sans",Om="blue",Nm="Open Sans",Bm=(0,Bn.createContext)(Am),Su=(0,Bn.createContext)({theme:"",mode:pP,themeNext:!1,corner:_m,UNSTABLE_corner:_m,headingFont:Lm,UNSTABLE_headingFont:Lm,accent:Om,UNSTABLE_accent:Om,actionFont:Nm,UNSTABLE_actionFont:Nm}),kw=(0,Bn.createContext)(Em);function Tw({applyClassesTo:e,children:t,density:n,theme:r,mode:o,breakpoints:a,themeNext:l,corner:i,headingFont:s,accent:c,actionFont:d}){let p=(0,Bn.useContext)(Pm),g=(0,Bn.useContext)(Bm),{theme:m,mode:b,corner:h,headingFont:y,accent:v,actionFont:u}=(0,Bn.useContext)(Su),f=p===null,x=n??g??Am,C=r??(m===""?Sw:m),k=o??b,T=a??Em,z=i??h??_m,O=s??y??Lm,A=c??v??Om,B=d??u??Nm,D=Y();J({testId:"salt-provider",css:ww,window:D});let N=(0,Bn.useMemo)(()=>({theme:C,mode:k,window:D,themeNext:!!l,corner:z,headingFont:O,accent:A,actionFont:B,UNSTABLE_corner:z,UNSTABLE_headingFont:O,UNSTABLE_accent:A,UNSTABLE_actionFont:B}),[C,k,D,l,z,O,A,B]),R=yw(T),P=(0,en.jsx)(Pm.Provider,{value:{targetWindow:D},children:(0,en.jsx)(Bm.Provider,{value:x,children:(0,en.jsx)(Su.Provider,{value:N,children:(0,en.jsx)(xw,{matchedBreakpoints:R,children:(0,en.jsx)(kw.Provider,{value:T,children:(0,en.jsx)(cw,{children:(0,en.jsx)(Cw,{applyClassesTo:e??(f?"root":"scope"),density:x,theme:V(Sw,{[fP]:l},C),mode:k,accent:l?A:void 0,actionFont:l?B:void 0,headingFont:l?O:void 0,corner:l?z:void 0,children:t})})})})})})});return f?(0,en.jsx)(vw,{children:P}):P}function Fm({enableStyleInjection:e,...t}){return(0,en.jsx)(Kc,{value:e,children:(0,en.jsx)(Tw,{...t})})}function Li({enableStyleInjection:e,...t}){return(0,en.jsx)(Kc,{value:e,children:(0,en.jsx)(Tw,{...t,themeNext:!0})})}var Mm=()=>{let{window:e,...t}=(0,Bn.useContext)(Su);return t};function ku(...e){return e.reduce((t,n)=>n==null?t:function(...o){t.apply(this,o),n.apply(this,o)},()=>{})}var Dm=typeof document<"u"&&window.visualViewport,mP=new Set(["checkbox","radio","range","color","file","image","button","submit","reset"]),Tu=0,zm;function Pw(e={}){let{isDisabled:t}=e;ie(()=>{if(!t)return Tu++,Tu===1&&(wP()?zm=gP():zm=vP()),()=>{Tu--,Tu===0&&zm()}},[t])}function vP(){return ku(il(document.documentElement,"paddingRight",`${window.innerWidth-document.documentElement.clientWidth}px`),il(document.documentElement,"overflow","hidden"))}function gP(){let e,t,n=c=>{e=_w(c.target,!0),!(e===document.documentElement&&e===document.body)&&e instanceof HTMLElement&&window.getComputedStyle(e).overscrollBehavior==="auto"&&(t=il(e,"overscrollBehavior","contain"))},r=c=>{if(!e||e===document.documentElement||e===document.body){c.preventDefault();return}e.scrollHeight===e.clientHeight&&e.scrollWidth===e.clientWidth&&c.preventDefault()},o=()=>{t&&t()},a=c=>{let d=c.target;hP(d)&&(i(),d.style.transform="translateY(-2000px)",requestAnimationFrame(()=>{d.style.transform="",Dm&&(Dm.height<window.innerHeight?requestAnimationFrame(()=>{Rw(d)}):Dm.addEventListener("resize",()=>Rw(d),{once:!0}))}))},l=null,i=()=>{if(l)return;let c=()=>{window.scrollTo(0,0)},d=window.pageXOffset,p=window.pageYOffset;l=ku(Oi(window,"scroll",c),il(document.documentElement,"paddingRight",`${window.innerWidth-document.documentElement.clientWidth}px`),il(document.documentElement,"overflow","hidden"),il(document.body,"marginTop",`-${p}px`),()=>{window.scrollTo(d,p)}),window.scrollTo(0,0)},s=ku(Oi(document,"touchstart",n,{passive:!1,capture:!0}),Oi(document,"touchmove",r,{passive:!1,capture:!0}),Oi(document,"touchend",o,{passive:!1,capture:!0}),Oi(document,"focus",a,!0));return()=>{t?.(),l?.(),s()}}function il(e,t,n){let r=e.style[t];return e.style[t]=n,()=>{e.style[t]=r}}function Oi(e,t,n,r){return e.addEventListener(t,n,r),()=>{e.removeEventListener(t,n,r)}}function Rw(e){let t=document.scrollingElement||document.documentElement,n=e;for(;n&&n!==t;){let r=_w(n);if(r!==document.documentElement&&r!==document.body&&r!==n){let o=r.getBoundingClientRect().top,a=n.getBoundingClientRect().top;a>o+n.clientHeight&&(r.scrollTop+=a-o)}n=r.parentElement}}function hP(e){return e instanceof HTMLInputElement&&!mP.has(e.type)||e instanceof HTMLTextAreaElement||e instanceof HTMLElement&&e.isContentEditable}function Ew(e,t){if(!e)return!1;let n=window.getComputedStyle(e),r=/(auto|scroll)/.test(n.overflow+n.overflowX+n.overflowY);return r&&t&&(r=e.scrollHeight!==e.clientHeight||e.scrollWidth!==e.clientWidth),r}function _w(e,t){let n=e;for(Ew(n,t)&&(n=n.parentElement);n&&!Ew(n,t);)n=n.parentElement;return n||document.scrollingElement||document.documentElement}function Wm(e){var t;return typeof window<"u"&&window.navigator!=null?e.test(((t=window.navigator.userAgentData)==null?void 0:t.platform)||window.navigator.platform):!1}function Ru(e){let t=null;return()=>(t==null&&(t=e()),t)}var bP=Ru(()=>Wm(/^Mac/i)),xP=Ru(()=>Wm(/^iPhone/i)),yP=Ru(()=>Wm(/^iPad/i)||bP()&&navigator.maxTouchPoints>1),wP=Ru(()=>xP()||yP());var IP=(0,Rr.forwardRef)(function(t,n){let{open:r,top:o,left:a,position:l,width:i,height:s,focusManagerProps:c,lockScroll:d,style:p,...g}=t,m={...p,top:o,left:a,position:l},{themeNext:b}=Mm();Pw({isDisabled:!d||!r});let h=b?Li:Fm;return c&&r?(0,po.jsx)(Tm,{children:(0,po.jsx)(h,{applyClassesTo:"scope",children:(0,po.jsx)(ow,{...c,children:(0,po.jsx)("div",{style:m,...g,ref:n})})})}):r?(0,po.jsx)(Tm,{children:(0,po.jsx)(h,{applyClassesTo:"scope",children:(0,po.jsx)("div",{style:m,...g,ref:n})})}):null}),CP=(0,Rr.createContext)({Component:IP});function Eu(){return(0,Rr.useContext)(CP)}var SP=e=>e,kP={platform:Pi,middleware:SP,animationFrame:!1},TP=(0,Rr.createContext)(kP);function RP(){return(0,Rr.useContext)(TP)}var EP=[kr(),_i({limiter:xm()})];function sl(e){let{middleware:t=EP,open:n=!1,onOpenChange:r,...o}=e,a=(g,m,b)=>{d(),r?.(g,m,b)},{platform:l,middleware:i,animationFrame:s}=RP(),{refs:c,update:d,...p}=aw({...o,middleware:i(t),open:n,onOpenChange:a,whileElementsMounted:(...g)=>du(...g,{animationFrame:s}),platform:l});return{reference:c.setReference,floating:c.setFloating,refs:c,update:d,...p}}var PP=w(F());var jm=w(F());var Nw=w(E());var Lw=`/* Style applied to the root element */
.saltIcon {
  --icon-color: currentColor;
  --icon-size-multiplier: var(--saltIcon-size-multiplier, 1);
  --icon-base-size: var(--salt-size-icon, 12px);
  /**
   * Icon size will be the multiplier (an integer from the size prop) * the base size (set by the theme per density)
   * Icons should never be smaller than 12px for readability so we've added a max() to enforce this
   * Consumers can use --saltIcon-size variable to override this rule as an escape hatch
   */
  --icon-size: var(--saltIcon-size, max(calc(var(--icon-base-size) * var(--icon-size-multiplier)), 12px));
}

.saltIcon {
  fill: var(--saltIcon-color, var(--icon-color));
  display: inline-block;
  margin: var(--saltIcon-margin, 0);
  position: relative;
  width: var(--icon-size);
  height: var(--icon-size);
  min-width: var(--icon-size);
  min-height: var(--icon-size);
}

.saltIcon-primary {
  --icon-color: var(--salt-content-primary-foreground);
}

.saltIcon-secondary {
  --icon-color: var(--salt-content-secondary-foreground);
}
`;var Bw=e=>(...t)=>[e,...t].join("-"),Ow=Bw("saltIcon"),Pu=1,ue=(0,Nw.forwardRef)(function({"aria-hidden":t,"aria-label":n,children:r,className:o,color:a="inherit",size:l=Pu,style:i,...s},c){let d=Y();J({testId:"salt-icon",css:Lw,window:d});let p={...i,"--saltIcon-size-multiplier":`${l}`};return(0,jm.jsx)("svg",{className:V(Ow(),{[Ow(a)]:a!=="inherit"},o),style:p,role:t?void 0:"img","aria-label":t?void 0:n,"aria-hidden":t,...s,ref:c,children:(0,jm.jsx)("g",{"aria-hidden":!0,children:r})})});var Ni=w(F()),Aw=w(E());var Vm=(0,Aw.forwardRef)(function(t,n){return(0,Ni.jsxs)(ue,{"data-testid":"BankIcon","aria-label":"bank",viewBox:"0 0 12 12",ref:n,...t,children:[(0,Ni.jsx)("path",{d:"M5.5 4V3h1v1z"}),(0,Ni.jsx)("path",{fillRule:"evenodd",d:"m6 0 6 6h-2v5h2v1H0v-1h2V6H0zM3 6v5h1V6zm2 0v5h2V6zm3 0v5h1V6zM6 1.414 9.586 5H2.414z",clipRule:"evenodd"})]})});var Hm=w(F()),Fw=w(E());var $m=(0,Fw.forwardRef)(function(t,n){return(0,Hm.jsx)(ue,{"data-testid":"CalendarIcon","aria-label":"calendar",viewBox:"0 0 12 12",ref:n,...t,children:(0,Hm.jsx)("path",{d:"M4 0v1h4V0h1v1h3v11H0V1h3V0zm7 4H1v7h10zM9 2H8v1h1zM4 2H3v1h1z"})})});var Um=w(F()),Mw=w(E());var Bi=(0,Mw.forwardRef)(function(t,n){return(0,Um.jsx)(ue,{"data-testid":"CheckmarkIcon","aria-label":"checkmark",viewBox:"0 0 12 12",ref:n,...t,children:(0,Um.jsx)("path",{fillRule:"evenodd",d:"M4.952 9.294 10 3.73 8.9 2.706 4.875 7.163 3.027 5.446 2 6.546z",clipRule:"evenodd"})})});var Km=w(F()),Dw=w(E());var Ai=(0,Dw.forwardRef)(function(t,n){return(0,Km.jsx)(ue,{"data-testid":"CheckmarkSolidIcon","aria-label":"checkmark solid",viewBox:"0 0 12 12",ref:n,...t,children:(0,Km.jsx)("path",{fillRule:"evenodd",d:"M0 0h12v12H0zm10 3.729L4.952 9.294 2 6.545l1.027-1.1 1.848 1.718L8.9 2.706z",clipRule:"evenodd"})})});var Gm=w(F()),zw=w(E());var _u=(0,zw.forwardRef)(function(t,n){return(0,Gm.jsx)(ue,{"data-testid":"ChevronDownIcon","aria-label":"chevron down",viewBox:"0 0 12 12",ref:n,...t,children:(0,Gm.jsx)("path",{d:"M5.618 8.593 6 9l.382-.407L11 3.661 10.236 3 6 7.524 1.764 3 1 3.66z"})})});var qm=w(F()),Ww=w(E());var Ym=(0,Ww.forwardRef)(function(t,n){return(0,qm.jsx)(ue,{"data-testid":"ChevronLeftIcon","aria-label":"chevron left",viewBox:"0 0 12 12",ref:n,...t,children:(0,qm.jsx)("path",{d:"M3.407 5.618 3 6l.407.382L8.339 11 9 10.236 4.476 6 9 1.764 8.34 1z"})})});var Qm=w(F()),jw=w(E());var Fi=(0,jw.forwardRef)(function(t,n){return(0,Qm.jsx)(ue,{"data-testid":"ChevronRightIcon","aria-label":"chevron right",viewBox:"0 0 12 12",ref:n,...t,children:(0,Qm.jsx)("path",{d:"M8.593 5.618 9 6l-.407.382L3.661 11 3 10.236 7.524 6 3 1.764 3.66 1z"})})});var Xm=w(F()),Vw=w(E());var Zm=(0,Vw.forwardRef)(function(t,n){return(0,Xm.jsx)(ue,{"data-testid":"ChevronUpIcon","aria-label":"chevron up",viewBox:"0 0 12 12",ref:n,...t,children:(0,Xm.jsx)("path",{d:"M5.618 3.407 6 3l.382.407L11 8.339 10.236 9 6 4.476 1.764 9 1 8.34z"})})});var Jm=w(F()),Hw=w(E());var Mi=(0,Hw.forwardRef)(function(t,n){return(0,Jm.jsx)(ue,{"data-testid":"CloseIcon","aria-label":"close",viewBox:"0 0 12 12",ref:n,...t,children:(0,Jm.jsx)("path",{d:"m5.999 5.292 3.89-3.888.707.707L6.707 6l3.889 3.889-.707.708-3.89-3.89-3.889 3.89-.707-.708L5.292 6 1.403 2.111l.707-.708z"})})});var Di=w(F()),$w=w(E());var ev=(0,$w.forwardRef)(function(t,n){return(0,Di.jsxs)(ue,{"data-testid":"DoubleChevronLeftIcon","aria-label":"double chevron left",viewBox:"0 0 12 12",ref:n,...t,children:[(0,Di.jsx)("path",{d:"M11.5 10.401 7.192 6 11.5 1.599 10.508.5 5 6l5.508 5.5z"}),(0,Di.jsx)("path",{d:"M7 10.401 2.692 6 7 1.599 6.008.5.5 6l5.508 5.5z"})]})});var zi=w(F()),Uw=w(E());var tv=(0,Uw.forwardRef)(function(t,n){return(0,zi.jsxs)(ue,{"data-testid":"DoubleChevronRightIcon","aria-label":"double chevron right",viewBox:"0 0 12 12",ref:n,...t,children:[(0,zi.jsx)("path",{d:"M.5 1.599 4.808 6 .5 10.401l.992 1.099L7 6 1.492.5z"}),(0,zi.jsx)("path",{d:"M5 1.599 9.308 6 5 10.401l.992 1.099L11.5 6 5.992.5z"})]})});var nv=w(F()),Kw=w(E());var rv=(0,Kw.forwardRef)(function(t,n){return(0,nv.jsx)(ue,{"data-testid":"ErrorSolidIcon","aria-label":"error solid",viewBox:"0 0 12 12",ref:n,...t,children:(0,nv.jsx)("path",{fillRule:"evenodd",d:"M9 0H3L0 3v6l3 3h6l3-3V3zM7 2H5v5h2zm-1 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2",clipRule:"evenodd"})})});var ov=w(F()),Gw=w(E());var av=(0,Gw.forwardRef)(function(t,n){return(0,ov.jsx)(ue,{"data-testid":"FavoriteIcon","aria-label":"favorite",viewBox:"0 0 12 12",ref:n,...t,children:(0,ov.jsx)("path",{d:"M6.448.302a.501.501 0 0 0-.902 0l-1.55 3.214-3.57.684a.5.5 0 0 0-.276.827L2.596 7.71l-.592 3.69a.5.5 0 0 0 .716.526l3.277-1.618 3.35 1.647a.5.5 0 0 0 .647-.555l-.591-3.69 2.446-2.683a.5.5 0 0 0-.276-.827l-3.57-.684zm.872 4.1 3.189.61-2.17 2.382.515 3.208-2.857-1.408L3.145 10.6l.515-3.207-2.17-2.382 3.189-.61 1.32-2.734z"})})});var lv=w(F()),qw=w(E());var iv=(0,qw.forwardRef)(function(t,n){return(0,lv.jsx)(ue,{"data-testid":"FavoriteSolidIcon","aria-label":"favorite solid",viewBox:"0 0 12 12",ref:n,...t,children:(0,lv.jsx)("path",{d:"M6.448.302a.501.501 0 0 0-.902 0l-1.55 3.214-3.57.684a.5.5 0 0 0-.276.827L2.596 7.71l-.592 3.69a.5.5 0 0 0 .716.526l3.277-1.618 3.35 1.647a.5.5 0 0 0 .647-.555l-.591-3.69 2.446-2.683a.5.5 0 0 0-.276-.827l-3.57-.684z"})})});var sv=w(F()),Yw=w(E());var cv=(0,Yw.forwardRef)(function(t,n){return(0,sv.jsx)(ue,{"data-testid":"FavoriteStrongIcon","aria-label":"favorite strong",viewBox:"0 0 12 12",ref:n,...t,children:(0,sv.jsx)("path",{d:"M5.547.303a.5.5 0 0 1 .901 0l1.554 3.213 3.57.684a.5.5 0 0 1 .278.827L9.403 7.71l.591 3.69a.5.5 0 0 1-.582.571l-.064-.016-3.351-1.648-3.276 1.619-.07.028a.5.5 0 0 1-.647-.556l.593-3.688L.15 5.027A.5.5 0 0 1 .426 4.2l3.57-.684zm-.528 4.544-2.557.49 1.73 1.897-.4 2.49 1.54-.76.663-.329 2.21 1.087-.397-2.488 1.728-1.897-2.557-.49-.327-.678-.654-1.352z"})})});var uv=w(F()),Qw=w(E());var dv=(0,Qw.forwardRef)(function(t,n){return(0,uv.jsx)(ue,{"data-testid":"InfoSolidIcon","aria-label":"info solid",viewBox:"0 0 12 12",ref:n,...t,children:(0,uv.jsx)("path",{fillRule:"evenodd",d:"M0 0h12v12H0zm6 2a1 1 0 1 1 0 2 1 1 0 0 1 0-2m1 3v5H5V5z",clipRule:"evenodd"})})});var Wi=w(F()),Xw=w(E());var fv=(0,Xw.forwardRef)(function(t,n){return(0,Wi.jsxs)(ue,{"data-testid":"LockedIcon","aria-label":"locked",viewBox:"0 0 12 12",ref:n,...t,children:[(0,Wi.jsx)("path",{d:"M6.5 8.915a1.5 1.5 0 1 0-1 0V10h1z"}),(0,Wi.jsx)("path",{fillRule:"evenodd",d:"M2 4H0v8h12V4h-2V2a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2zm1-2a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2H3zm-2 9V5h10v6z",clipRule:"evenodd"})]})});var pv=w(F()),Zw=w(E());var mv=(0,Zw.forwardRef)(function(t,n){return(0,pv.jsx)(ue,{"data-testid":"OverflowMenuIcon","aria-label":"overflow menu",viewBox:"0 0 12 12",ref:n,...t,children:(0,pv.jsx)("path",{d:"M1 5h2v2H1zm4 0h2v2H5zm6 0H9v2h2z"})})});var vv=w(F()),Jw=w(E());var gv=(0,Jw.forwardRef)(function(t,n){return(0,vv.jsx)(ue,{"data-testid":"ProgressInprogressIcon","aria-label":"progress inprogress",viewBox:"0 0 12 12",ref:n,...t,children:(0,vv.jsx)("path",{fillRule:"evenodd",d:"M12 6A6 6 0 1 1 0 6a6 6 0 0 1 12 0M1 6a5 5 0 0 1 5-5v10a5 5 0 0 1-5-5",clipRule:"evenodd"})})});var hv=w(F()),eI=w(E());var bv=(0,eI.forwardRef)(function(t,n){return(0,hv.jsx)(ue,{"data-testid":"RefreshIcon","aria-label":"refresh",viewBox:"0 0 12 12",ref:n,...t,children:(0,hv.jsx)("path",{d:"M4.707 10.831a5 5 0 1 1 5.625-7.33h-2.33v1h4v-4h-1v2.184A6 6 0 0 0 9.745 1.31a6 6 0 1 0 2.052 6.244l-.966-.26a5 5 0 0 1-6.124 3.536"})})});var xv=w(F()),tI=w(E());var Lu=(0,tI.forwardRef)(function(t,n){return(0,xv.jsx)(ue,{"data-testid":"SearchIcon","aria-label":"search",viewBox:"0 0 12 12",ref:n,...t,children:(0,xv.jsx)("path",{fillRule:"evenodd",d:"M8 9a5 5 0 1 1 1-1l3 3-1 1zm1-4a4 4 0 1 1-8 0 4 4 0 0 1 8 0",clipRule:"evenodd"})})});var yv=w(F()),nI=w(E());var wv=(0,nI.forwardRef)(function(t,n){return(0,yv.jsx)(ue,{"data-testid":"StepActiveIcon","aria-label":"step active",viewBox:"0 0 12 12",ref:n,...t,children:(0,yv.jsx)("path",{fillRule:"evenodd",d:"M6 12A6 6 0 1 0 6 0a6 6 0 0 0 0 12",clipRule:"evenodd"})})});var Iv=w(F()),rI=w(E());var Cv=(0,rI.forwardRef)(function(t,n){return(0,Iv.jsx)(ue,{"data-testid":"StepDefaultIcon","aria-label":"step default",viewBox:"0 0 12 12",ref:n,...t,children:(0,Iv.jsx)("path",{fillRule:"evenodd",d:"M6 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8m6-4A6 6 0 1 1 0 6a6 6 0 0 1 12 0",clipRule:"evenodd"})})});var Sv=w(F()),oI=w(E());var Ou=(0,oI.forwardRef)(function(t,n){return(0,Sv.jsx)(ue,{"data-testid":"SuccessCircleSolidIcon","aria-label":"success circle solid",viewBox:"0 0 12 12",ref:n,...t,children:(0,Sv.jsx)("path",{fillRule:"evenodd",d:"M6 12A6 6 0 1 0 6 0a6 6 0 0 0 0 12m3.75-7.984L4.952 9.332 2 6.582l1.027-1.098L4.875 7.2l3.772-4.208z",clipRule:"evenodd"})})});var ji=w(F()),aI=w(E());var kv=(0,aI.forwardRef)(function(t,n){return(0,ji.jsxs)(ue,{"data-testid":"TearOutIcon","aria-label":"tear out",viewBox:"0 0 12 12",ref:n,...t,children:[(0,ji.jsx)("path",{d:"M0 12h12V6h-1v5H1V1h5V0H0z"}),(0,ji.jsx)("path",{d:"M11.996 4V0h-4v1h2.293L5.996 5.293 6.703 6l4.293-4.293V4z"})]})});var Tv=w(F()),lI=w(E());var Rv=(0,lI.forwardRef)(function(t,n){return(0,Tv.jsx)(ue,{"data-testid":"TriangleDownIcon","aria-label":"triangle down",viewBox:"0 0 12 12",ref:n,...t,children:(0,Tv.jsx)("path",{d:"m6 8.5 5-5H1z"})})});var Ev=w(F()),iI=w(E());var Pv=(0,iI.forwardRef)(function(t,n){return(0,Ev.jsx)(ue,{"data-testid":"TriangleUpIcon","aria-label":"triangle up",viewBox:"0 0 12 12",ref:n,...t,children:(0,Ev.jsx)("path",{d:"m6 3.5-5 5h10z"})})});var _v=w(F()),sI=w(E());var Lv=(0,sI.forwardRef)(function(t,n){return(0,_v.jsx)(ue,{"data-testid":"UploadIcon","aria-label":"upload",viewBox:"0 0 12 12",ref:n,...t,children:(0,_v.jsx)("path",{d:"M6.5 9.028h-1V1.914L2.818 4.596l-.707-.707L6 0l3.889 3.89-.707.706L6.5 1.914zM12 11v1H0v-1z"})})});var Ov=w(F()),cI=w(E());var Nv=(0,cI.forwardRef)(function(t,n){return(0,Ov.jsx)(ue,{"data-testid":"UserIcon","aria-label":"user",viewBox:"0 0 12 12",ref:n,...t,children:(0,Ov.jsx)("path",{fillRule:"evenodd",d:"M12 11v.996H6V12H0v-.996q0-.68.41-1.206a1.96 1.96 0 0 1 1.02-.715q.14-.06.328-.117.176-.06.422-.129.059-.012.14-.035.083-.024.223-.07l.2-.047q.082-.035.163-.059.785-.234 1.184-.539.398-.304.492-.785a4.5 4.5 0 0 1-.644-.867 6 6 0 0 1-.493-1.077 8 8 0 0 1-.328-1.172A6.3 6.3 0 0 1 3 3.003q0-.82.234-1.394T3.88.683q.41-.363.95-.515Q5.378.004 6 .004V0q.621 0 1.172.164a2.4 2.4 0 0 1 1.594 1.441Q9 2.179 9 2.999q0 .574-.117 1.183a8 8 0 0 1-.328 1.172 6 6 0 0 1-.492 1.077q-.293.504-.645.867.094.48.492.785.398.304 1.184.54.082.022.164.058l.199.047q.14.046.223.07.081.023.14.035.246.07.422.129.188.059.328.117a1.96 1.96 0 0 1 1.02.715Q12 10.32 12 11M6 1.007v.004q-1.008 0-1.5.469-.504.457-.504 1.523 0 .492.106 1.007a6 6 0 0 0 .68 1.887q.233.42.515.702l.351.364-.082.503q-.14.82-.726 1.312-.586.48-1.64.809a1 1 0 0 0-.177.058 5 5 0 0 1-.21.047q-.177.06-.235.082l-.129.024-.375.117a2 2 0 0 0-.258.094l-.105.035a.97.97 0 0 0-.516.363 1 1 0 0 0-.199.597H6V11h5.004a.98.98 0 0 0-.2-.597.97.97 0 0 0-.515-.363l-.105-.035a2 2 0 0 0-.258-.094l-.375-.117-.13-.024a5 5 0 0 0-.233-.082 5 5 0 0 1-.211-.047 1 1 0 0 0-.176-.058q-1.055-.328-1.64-.809-.587-.492-.727-1.312l-.082-.503.351-.363a3.2 3.2 0 0 0 .516-.703q.234-.41.41-.89t.27-.996q.105-.516.105-1.008 0-1.065-.504-1.523-.492-.469-1.5-.469",clipRule:"evenodd"})})});var Bv=w(F()),uI=w(E());var Av=(0,uI.forwardRef)(function(t,n){return(0,Bv.jsx)(ue,{"data-testid":"WarningSolidIcon","aria-label":"warning solid",viewBox:"0 0 12 12",ref:n,...t,children:(0,Bv.jsx)("path",{fillRule:"evenodd",d:"m6 0 6 12H0zM5 5h2v3H5zm2 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0",clipRule:"evenodd"})})});var Nu=w(E());var Fv=w(F()),dI=w(E()),fI=(0,dI.forwardRef)(function({children:t,className:n,...r},o){return(0,Fv.jsx)("svg",{className:n,...r,role:"img",ref:o,viewBox:"0 0 8 8",children:(0,Fv.jsx)("path",{fillRule:"evenodd",clipRule:"evenodd",d:"M4 8C6.20914 8 8 6.20914 8 4C8 1.79086 6.20914 0 4 0C1.79086 0 0 1.79086 0 4C0 6.20914 1.79086 8 4 8Z"})})});var Mv=w(F()),pI=w(E()),mI=(0,pI.forwardRef)(function({children:t,className:n,...r},o){return(0,Mv.jsx)("svg",{className:n,...r,role:"img",viewBox:"0 0 10 8",ref:o,children:(0,Mv.jsx)("path",{fillRule:"evenodd",clipRule:"evenodd",d:"M2.92089 5.95735L8.96399 0L10 1.02133L2.92088 8L0 5.1205L1.03602 4.09918L2.92089 5.95735Z"})})});var Dv=w(F()),vI=w(E()),gI=(0,vI.forwardRef)(function({children:t,className:n,...r},o){return(0,Dv.jsx)("svg",{className:n,...r,role:"img",viewBox:"0 0 9 8",ref:o,children:(0,Dv.jsx)("path",{d:"M0 8L4.5 0L9 8H0Z"})})});var hI={ActiveIcon:wv,CalendarIcon:$m,CloseIcon:Mi,CollapseGroupIcon:_u,CollapseIcon:Zm,CollapseLeftIcon:ev,CollapseRightIcon:tv,CompletedIcon:Ou,DecreaseIcon:Rv,EntityIcon:Vm,ErrorIcon:rv,ErrorStatusAdornment:fI,ExpandGroupIcon:Fi,ExpandIcon:_u,ExternalIcon:kv,IncreaseIcon:Pv,InfoIcon:dv,InProgressIcon:gv,LockedIcon:fv,LevelSeparatorIcon:Fi,NextIcon:Fi,OverflowIcon:mv,PendingIcon:Cv,PreviousIcon:Ym,RatingIcon:av,RatingSelectedIcon:iv,RatingUnselectingIcon:cv,SuccessIcon:Ou,SuccessStatusAdornment:mI,UploadIcon:Lv,UserIcon:Nv,WarningIcon:Av,WarningStatusAdornment:gI},_P=(0,Nu.createContext)(hI);var vn=()=>(0,Nu.useContext)(_P)||hI;var yI=w(F());var wI=w(E());function or(e){return e.length>0?e[0].toUpperCase()+e.slice(1):e}var bI=`.saltStatusIndicator {
  --statusIndicator-warning-color: var(--salt-status-warning-foreground-decorative);
  --statusIndicator-info-color: var(--salt-status-info-foreground-decorative);
  --statusIndicator-success-color: var(--salt-status-success-foreground-decorative);
  --statusIndicator-error-color: var(--salt-status-error-foreground-decorative);
  color: var(--saltStatusIndicator-color, var(--statusIndicator-Color));
}

.saltStatusIndicator-error {
  --statusIndicator-Color: var(--statusIndicator-error-color);
}

.saltStatusIndicator-warning {
  --statusIndicator-Color: var(--statusIndicator-warning-color);
}

.saltStatusIndicator-success {
  --statusIndicator-Color: var(--statusIndicator-success-color);
}

.saltStatusIndicator-info {
  --statusIndicator-Color: var(--statusIndicator-info-color);
}
`;var xI=te("saltStatusIndicator"),Bu=(0,wI.forwardRef)(function({className:t,status:n,size:r=Pu,...o},a){let l=Y();J({testId:"salt-status-indicator",css:bI,window:l});let i=vn(),c=`${or(n)}Icon`,d=i[c],p=n;return d===void 0?null:(0,yI.jsx)(d,{className:V(xI(),xI(n),t),size:r,"aria-label":p,...o,ref:a})});var ea=w(E());function II(e,t=166,n=!1){let r,o=function(...l){let i=()=>{e.apply(this,l)};clearTimeout(r),n&&i(),r=window.setTimeout(i,t)};return o.clear=()=>{clearTimeout(r)},o}var lA=w(F());var Au=({debounce:e=0}={})=>{let t=(0,ea.useContext)(yu),n=(0,ea.useCallback)((o,a={})=>{let l=typeof a=="number",i,s={};l?i=a:s=a;let c=t?.announce;function d(){if(s.target){let p=fw(s.target);if(p){let{target:g,...m}=s;p(o,m);return}}c&&t.announce(o,l?i:s)}i?setTimeout(d,i):d()},[t]),r=(0,ea.useMemo)(()=>e>0?II(n,e):n,[n,e]);return(0,ea.useMemo)(()=>({...t,announce:r}),[t,r])};var Mu=w(F());var EI=w(E());var RI=`/* Styles applied to root component */
.saltBanner {
  --banner-background: var(--salt-container-primary-background);

  background: var(--saltBanner-background, var(--banner-background));
  border-color: var(--saltBanner-borderColor, var(--banner-borderColor));
  border-width: var(--saltBanner-borderWidth, var(--salt-size-fixed-100));
  border-style: var(--saltBanner-borderStyle, var(--salt-borderStyle-solid));
  border-radius: var(--saltBanner-borderRadius, var(--salt-palette-corner, 0));
  box-sizing: border-box;
  display: inline-flex;
  gap: var(--salt-spacing-75);
  padding: var(--saltBanner-padding, var(--salt-spacing-50) var(--salt-spacing-100));
  width: 100%;
  min-height: calc(var(--salt-size-base) + var(--salt-spacing-100));

  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-fontWeight);
  line-height: var(--salt-text-lineHeight);
  letter-spacing: var(--salt-text-letterSpacing);
  color: var(--salt-content-primary-foreground);
}

/* Styles applied to icon */
.saltBanner-icon.saltIcon {
  min-height: var(--salt-size-base);
}

/* Styles applied when state = "info" */
.saltBanner-info {
  --banner-borderColor: var(--salt-status-info-borderColor);
}

/* Styles applied when state = "error" */
.saltBanner-error {
  --banner-borderColor: var(--salt-status-error-borderColor);
}

/* Styles applied when state = "warning" */
.saltBanner-warning {
  --banner-borderColor: var(--salt-status-warning-borderColor);
}

/* Styles applied when state = "success" */
.saltBanner-success {
  --banner-borderColor: var(--salt-status-success-borderColor);
}

.saltBanner-secondary.saltBanner-info {
  --banner-background: var(--salt-status-info-background);
}

.saltBanner-secondary.saltBanner-error {
  --banner-background: var(--salt-status-error-background);
}

.saltBanner-secondary.saltBanner-warning {
  --banner-background: var(--salt-status-warning-background);
}

.saltBanner-secondary.saltBanner-success {
  --banner-background: var(--salt-status-success-background);
}
`;var Fu=te("saltBanner"),mo=(0,EI.forwardRef)(function({children:t,className:n,variant:r="primary",status:o="info",...a},l){let i=Y();return J({testId:"salt-banner",css:RI,window:i}),(0,Mu.jsxs)("div",{className:V(Fu(),Fu(o),Fu(r),n),ref:l,...a,children:[(0,Mu.jsx)(Bu,{"aria-hidden":!0,status:o,className:Fu("icon")}),t]})});var _I=w(F());var LI=w(E());var PI=`.saltBannerActions {
  margin-bottom: auto;
  display: flex;
  gap: var(--salt-spacing-100);
  align-items: center;
  min-height: var(--salt-size-base);
}
`;var WP=te("saltBannerActions"),Wv=(0,LI.forwardRef)(function(t,n){let{className:r,...o}=t,a=Y();return J({testId:"salt-banner-actions",css:PI,window:a}),(0,_I.jsx)("div",{className:V(WP(),r),...o,ref:n})});var NI=w(F());var BI=w(E());var OI=`/* Styles applied to BannerContent */
.saltBannerContent {
  flex: 1 0;
  margin: var(--salt-spacing-75) 0;
}
`;var jP=te("saltBannerContent"),vo=(0,BI.forwardRef)(function(t,n){let{className:r,...o}=t,a=Y();return J({testId:"salt-banner-content",css:OI,window:a}),(0,NI.jsx)("div",{className:V(jP(),r),...o,ref:n})});function Du(e){return e===void 0||typeof e=="string"?e:`calc(var(--salt-spacing-100) * ${e})`}function VP(e){return typeof e=="object"&&!Array.isArray(e)}function Er(e,t){if(e&&VP(e)){for(let n of t)if(e[n]!=null)return e[n];return}return e}var AI=w(E());function jv(e,t){typeof e=="function"?e(t):e&&(e.current=t)}function Ee(e,t){return(0,AI.useMemo)(()=>e==null&&t==null?()=>null:n=>{jv(e,n),jv(t,n)},[e,t])}var dl=w(F());var WI=w(E());var Vv=w(F());var zu=w(E());var FI=`/* Styles applied to the root element */
.saltSpinner {
  position: relative;
}

/* Styles applied to the SVG stop elements */
.saltSpinner-gradientStop {
  stop-color: var(--saltSpinner-gradient-color, var(--salt-sentiment-accent-background));
}

/* Styles applied when \`size="medium"\` */
.saltSpinner-medium {
  --spinner-strokeWidth: var(--salt-size-bar);
  height: var(--salt-size-base);
  width: var(--salt-size-base);
}
.saltSpinner-medium .saltSpinner-arc {
  r: calc((var(--salt-size-base) - var(--spinner-strokeWidth)) / 2);
}

/* Styles applied when \`size="large"\` */
.saltSpinner-large {
  --spinner-strokeWidth: var(--salt-size-bar);
  height: calc(var(--salt-size-base) * 2);
  width: calc(var(--salt-size-base) * 2);
}
.saltSpinner-large .saltSpinner-arc {
  r: calc((var(--salt-size-base) * 2 - var(--spinner-strokeWidth)) / 2);
}

/* Styles applied when \`size="small"\` */
.saltSpinner-small {
  --spinner-strokeWidth: var(--salt-size-fixed-200);
  height: max(var(--salt-size-icon), 12px);
  width: max(var(--salt-size-icon), 12px);
}
.saltSpinner-small .saltSpinner-arc {
  r: calc((max(var(--salt-size-icon), 12px) - var(--spinner-strokeWidth)) / 2);
}

/* Styles applied to the SVG */
.saltSpinner-spinner {
  animation: spinner 0.9s linear infinite;
  width: 100%;
  height: 100%;
  position: absolute;
  left: 0;
  top: 0;
}

@keyframes spinner {
  0% {
    transform: rotate(0);
  }
  100% {
    transform: rotate(360deg);
  }
}
`;var Pr=w(F()),WA=w(E());var Vi=te("saltSpinner"),MI=({id:e="svg-spinner",...t})=>{let n=`${e}-1`;return(0,Pr.jsxs)("svg",{className:Vi("spinner"),preserveAspectRatio:"xMidYMid meet",id:e,...t,children:[(0,Pr.jsx)("defs",{children:(0,Pr.jsxs)("linearGradient",{id:n,x1:"0",y1:"0",x2:"50%",y2:"0",children:[(0,Pr.jsx)("stop",{className:Vi("gradientStop"),offset:"15%",stopOpacity:"1"}),(0,Pr.jsx)("stop",{className:Vi("gradientStop"),offset:"100%",stopOpacity:"0"})]})}),(0,Pr.jsx)("circle",{className:Vi("arc"),cx:"50%",cy:"50%",fill:"none",stroke:"var(--saltSpinner-gradient-color, var(--salt-sentiment-accent-background))",strokeWidth:"var(--spinner-strokeWidth)",pathLength:"100",strokeDasharray:"50 50",strokeDashoffset:"50"}),(0,Pr.jsx)("circle",{className:Vi("arc"),cx:"50%",cy:"50%",fill:"none",stroke:`url(#${n})`,strokeWidth:"var(--spinner-strokeWidth)",pathLength:"100",strokeDasharray:"50 50",strokeDashoffset:"75"})]})};var HP=e=>e==="default"?"medium":e,DI=te("saltSpinner"),ul=(0,zu.forwardRef)(function({"aria-label":t="loading",announcerInterval:n=5e3,announcerTimeout:r=2e4,completionAnnouncement:o=`finished ${t}`,disableAnnouncer:a,className:l,size:i="medium",id:s,...c},d){let p=We(s),g=Y();J({testId:"salt-spinner",css:FI,window:g});let{announce:m}=Au(),b=HP(i);return(0,zu.useEffect)(()=>{if(a)return;m(t);let h=Date.now(),y=n>0&&setInterval(()=>{if(Date.now()-h>r){m(`${t} is still in progress, but will no longer announce.`),y&&clearInterval(y);return}m(t)},n);return()=>{a||(y&&clearInterval(y),o&&m(o))}},[m,n,r,t,o,a]),(0,Vv.jsx)("div",{"aria-label":t,className:V(DI(),DI(b),l),ref:d,role:"img",...c,children:(0,Vv.jsx)(MI,{id:p})})});var zI=`.saltButton {
  --button-borderWidth: var(--salt-size-fixed-100);

  align-items: var(--saltButton-alignItems, center);
  appearance: none;
  background: var(--saltButton-background, var(--button-background));
  border-color: var(--saltButton-borderColor, var(--button-borderColor, transparent));
  border-style: var(--saltButton-borderStyle, solid);
  border-width: var(--saltButton-borderWidth, var(--button-borderWidth));
  border-radius: var(--saltButton-borderRadius, var(--salt-palette-corner-weak, 0));
  color: var(--saltButton-text-color, var(--button-text-color));
  display: inline-flex;
  gap: var(--salt-spacing-50);
  justify-content: var(--saltButton-justifyContent, center);
  font-size: var(--saltButton-fontSize, var(--salt-text-fontSize));
  font-family: var(--saltButton-fontFamily, var(--salt-text-action-fontFamily));
  line-height: var(--saltButton-lineHeight, var(--salt-text-lineHeight));
  letter-spacing: var(--saltButton-letterSpacing, var(--salt-text-action-letterSpacing));
  text-transform: var(--saltButton-textTransform, var(--salt-text-action-textTransform));
  padding: 0 var(--saltButton-padding, calc(var(--salt-spacing-100) - var(--saltButton-borderWidth, var(--button-borderWidth))));
  margin: var(--saltButton-margin, 0);
  height: var(--saltButton-height, var(--salt-size-base));
  min-width: var(--saltButton-minWidth, unset);
  position: relative;
  text-align: var(--saltButton-textAlign, var(--salt-text-action-textAlign));
  text-decoration: none;
  transition: none;
  width: var(--saltButton-width, auto);
  -webkit-appearance: none;
  -webkit-tap-highlight-color: transparent;
  /* Styles applied to align children*/
  font-weight: var(--saltButton-fontWeight, var(--salt-text-action-fontWeight));
}

/* Pseudo-class applied to the root element on focus */
.saltButton:focus-visible {
  outline-style: var(--salt-focused-outlineStyle);
  outline-width: var(--salt-focused-outlineWidth);
  outline-color: var(--salt-focused-outlineColor);
  outline-offset: var(--salt-focused-outlineOffset);
  background: var(--saltButton-background-hover, var(--button-background-hover));
  color: var(--saltButton-text-color-hover, var(--button-text-color-hover));
  border-color: var(--saltButton-borderColor-hover, var(--button-borderColor-hover));
}

@media (hover: hover) {
  /* Pseudo-class applied to the root element on hover when Button is not active or disabled */
  .saltButton:hover {
    background: var(--saltButton-background-hover, var(--button-background-hover));
    color: var(--saltButton-text-color-hover, var(--button-text-color-hover));
    border-color: var(--saltButton-borderColor-hover, var(--button-borderColor-hover));
    cursor: var(--salt-cursor-hover);
  }
}

/* Pseudo-class applied to the root element when Button is active and not disabled */
.saltButton.saltButton-active:focus-visible,
.saltButton:focus-visible:active,
.saltButton:active,
.saltButton.saltButton-active {
  background: var(--saltButton-background-active, var(--button-background-active));
  color: var(--saltButton-text-color-active, var(--button-text-color-active));
  border-color: var(--saltButton-borderColor-active, var(--button-borderColor-active));
  cursor: var(--salt-cursor-active);
}

/* Styles applied when the button triggers a dialog or menu */
.saltButton[aria-expanded="true"][aria-haspopup="menu"],
.saltButton[aria-expanded="true"][aria-haspopup="dialog"] {
  background: var(--saltButton-background-active, var(--button-background-active));
  color: var(--saltButton-text-color-active, var(--button-text-color-active));
  border-color: var(--saltButton-borderColor-active, var(--button-borderColor-active));
}

/* Pseudo-class applied to the root element if disabled={true} */
.saltButton:disabled,
.saltButton.saltButton-disabled,
.saltButton.saltButton-disabled:active,
.saltButton.saltButton-disabled:focus-visible,
.saltButton.saltButton-disabled:focus-visible:active,
.saltButton.saltButton-disabled:hover {
  background: var(--saltButton-background-disabled, var(--button-background));
  color: var(--saltButton-text-color-disabled, var(--button-text-color));
  cursor: var(--saltButton-cursor-disabled, var(--salt-cursor-disabled));
  border-color: var(--saltButton-borderColor-disabled, var(--button-borderColor));

  opacity: 0.4;
}

.saltButton-accented.saltButton-solid {
  --button-text-color: var(--salt-actionable-accented-bold-foreground);
  --button-text-color-hover: var(--salt-actionable-accented-bold-foreground-hover);
  --button-text-color-active: var(--salt-actionable-accented-bold-foreground-active);
  --button-background: var(--salt-actionable-accented-bold-background);
  --button-background-active: var(--salt-actionable-accented-bold-background-active);
  --button-background-hover: var(--salt-actionable-accented-bold-background-hover);
  --button-borderColor: var(--salt-actionable-accented-bold-borderColor);
  --button-borderColor-hover: var(--salt-actionable-accented-bold-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-accented-bold-borderColor-active);
}

.saltButton-accented.saltButton-bordered {
  --button-text-color: var(--salt-actionable-accented-foreground);
  --button-text-color-hover: var(--salt-actionable-accented-foreground-hover);
  --button-text-color-active: var(--salt-actionable-accented-foreground-active);
  --button-background: var(--salt-actionable-accented-background);
  --button-background-hover: var(--salt-actionable-accented-background-hover);
  --button-background-active: var(--salt-actionable-accented-background-active);
  --button-borderColor: var(--salt-actionable-accented-borderColor);
  --button-borderColor-hover: var(--salt-actionable-accented-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-accented-borderColor-active);
}

.saltButton-accented.saltButton-transparent {
  --button-text-color: var(--salt-actionable-accented-subtle-foreground);
  --button-text-color-hover: var(--salt-actionable-accented-subtle-foreground-hover);
  --button-text-color-active: var(--salt-actionable-accented-subtle-foreground-active);
  --button-background: var(--salt-actionable-accented-subtle-background);
  --button-background-hover: var(--salt-actionable-accented-subtle-background-hover);
  --button-background-active: var(--salt-actionable-accented-subtle-background-active);
  --button-borderColor: var(--salt-actionable-accented-subtle-borderColor);
  --button-borderColor-hover: var(--salt-actionable-accented-subtle-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-accented-subtle-borderColor-active);
}

.saltButton-accented.saltButton-loading {
  --button-text-color: var(--salt-actionable-accented-background);
  --button-text-color-hover: var(--salt-actionable-accented-background);
  --button-text-color-active: var(--salt-actionable-accented-background);
  --button-background: var(--salt-actionable-accented-background);
  --button-background-hover: var(--salt-actionable-accented-background);
  --button-background-active: var(--salt-actionable-accented-background);
  --button-borderColor: var(--salt-actionable-accented-borderColor);
  --button-borderColor-hover: var(--salt-actionable-accented-borderColor);
  --button-borderColor-active: var(--salt-actionable-accented-borderColor);
  cursor: var(--salt-cursor-pending);
}

.saltButton-neutral.saltButton-solid {
  --button-text-color: var(--salt-actionable-bold-foreground);
  --button-text-color-hover: var(--salt-actionable-bold-foreground-hover);
  --button-text-color-active: var(--salt-actionable-bold-foreground-active);
  --button-background: var(--salt-actionable-bold-background);
  --button-background-hover: var(--salt-actionable-bold-background-hover);
  --button-background-active: var(--salt-actionable-bold-background-active);
  --button-borderColor: var(--salt-actionable-bold-borderColor);
  --button-borderColor-hover: var(--salt-actionable-bold-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-bold-borderColor-active);
}

.saltButton-neutral.saltButton-bordered {
  --button-text-color: var(--salt-actionable-foreground);
  --button-text-color-hover: var(--salt-actionable-foreground-hover);
  --button-text-color-active: var(--salt-actionable-foreground-active);
  --button-background: var(--salt-actionable-background);
  --button-background-hover: var(--salt-actionable-background-hover);
  --button-background-active: var(--salt-actionable-background-active);
  --button-borderColor: var(--salt-actionable-borderColor);
  --button-borderColor-hover: var(--salt-actionable-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-borderColor-active);
}

.saltButton-neutral.saltButton-transparent {
  --button-text-color: var(--salt-actionable-subtle-foreground);
  --button-text-color-hover: var(--salt-actionable-subtle-foreground-hover);
  --button-text-color-active: var(--salt-actionable-subtle-foreground-active);
  --button-background: var(--salt-actionable-subtle-background);
  --button-background-hover: var(--salt-actionable-subtle-background-hover);
  --button-background-active: var(--salt-actionable-subtle-background-active);
  --button-borderColor: var(--salt-actionable-subtle-borderColor);
  --button-borderColor-hover: var(--salt-actionable-subtle-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-subtle-borderColor-active);
}

.saltButton-neutral.saltButton-loading {
  --button-text-color: var(--salt-actionable-background);
  --button-text-color-hover: var(--salt-actionable-background);
  --button-text-color-active: var(--salt-actionable-background);
  --button-background: var(--salt-actionable-background);
  --button-background-hover: var(--salt-actionable-background);
  --button-background-active: var(--salt-actionable-background);
  --button-borderColor: var(--salt-actionable-borderColor);
  --button-borderColor-hover: var(--salt-actionable-borderColor);
  --button-borderColor-active: var(--salt-actionable-borderColor);
  cursor: var(--salt-cursor-pending);
}

.saltButton-negative.saltButton-solid {
  --button-text-color: var(--salt-actionable-negative-bold-foreground);
  --button-text-color-hover: var(--salt-actionable-negative-bold-foreground-hover);
  --button-text-color-active: var(--salt-actionable-negative-bold-foreground-active);
  --button-background: var(--salt-actionable-negative-bold-background);
  --button-background-hover: var(--salt-actionable-negative-bold-background-hover);
  --button-background-active: var(--salt-actionable-negative-bold-background-active);
  --button-borderColor: var(--salt-actionable-negative-bold-borderColor);
  --button-borderColor-hover: var(--salt-actionable-negative-bold-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-negative-bold-borderColor-active);
}

.saltButton-negative.saltButton-bordered {
  --button-text-color: var(--salt-actionable-negative-foreground);
  --button-text-color-hover: var(--salt-actionable-negative-foreground-hover);
  --button-text-color-active: var(--salt-actionable-negative-foreground-active);
  --button-background: var(--salt-actionable-negative-background);
  --button-background-hover: var(--salt-actionable-negative-background-hover);
  --button-background-active: var(--salt-actionable-negative-background-active);
  --button-borderColor: var(--salt-actionable-negative-borderColor);
  --button-borderColor-hover: var(--salt-actionable-negative-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-negative-borderColor-active);
}

.saltButton-negative.saltButton-transparent {
  --button-text-color: var(--salt-actionable-negative-subtle-foreground);
  --button-text-color-hover: var(--salt-actionable-negative-subtle-foreground-hover);
  --button-text-color-active: var(--salt-actionable-negative-subtle-foreground-active);
  --button-background: var(--salt-actionable-negative-subtle-background);
  --button-background-hover: var(--salt-actionable-negative-subtle-background-hover);
  --button-background-active: var(--salt-actionable-negative-subtle-background-active);
  --button-borderColor: var(--salt-actionable-negative-subtle-borderColor);
  --button-borderColor-hover: var(--salt-actionable-negative-subtle-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-negative-subtle-borderColor-active);
}

.saltButton-negative.saltButton-loading {
  --button-text-color: var(--salt-actionable-negative-background);
  --button-text-color-hover: var(--salt-actionable-negative-background);
  --button-text-color-active: var(--salt-actionable-negative-background);
  --button-background: var(--salt-actionable-negative-background);
  --button-background-hover: var(--salt-actionable-negative-background);
  --button-background-active: var(--salt-actionable-negative-background);
  --button-borderColor: var(--salt-actionable-negative-borderColor);
  --button-borderColor-hover: var(--salt-actionable-negative-borderColor);
  --button-borderColor-active: var(--salt-actionable-negative-borderColor);
  cursor: var(--salt-cursor-pending);
}

.saltButton-positive.saltButton-solid {
  --button-text-color: var(--salt-actionable-positive-bold-foreground);
  --button-text-color-hover: var(--salt-actionable-positive-bold-foreground-hover);
  --button-text-color-active: var(--salt-actionable-positive-bold-foreground-active);
  --button-background: var(--salt-actionable-positive-bold-background);
  --button-background-hover: var(--salt-actionable-positive-bold-background-hover);
  --button-background-active: var(--salt-actionable-positive-bold-background-active);
  --button-borderColor: var(--salt-actionable-positive-bold-borderColor);
  --button-borderColor-hover: var(--salt-actionable-positive-bold-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-positive-bold-borderColor-active);
}

.saltButton-positive.saltButton-bordered {
  --button-text-color: var(--salt-actionable-positive-foreground);
  --button-text-color-hover: var(--salt-actionable-positive-foreground-hover);
  --button-text-color-active: var(--salt-actionable-positive-foreground-active);
  --button-background: var(--salt-actionable-positive-background);
  --button-background-hover: var(--salt-actionable-positive-background-hover);
  --button-background-active: var(--salt-actionable-positive-background-active);
  --button-borderColor: var(--salt-actionable-positive-borderColor);
  --button-borderColor-hover: var(--salt-actionable-positive-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-positive-borderColor-active);
}

.saltButton-positive.saltButton-transparent {
  --button-text-color: var(--salt-actionable-positive-subtle-foreground);
  --button-text-color-hover: var(--salt-actionable-positive-subtle-foreground-hover);
  --button-text-color-active: var(--salt-actionable-positive-subtle-foreground-active);
  --button-background: var(--salt-actionable-positive-subtle-background);
  --button-background-hover: var(--salt-actionable-positive-subtle-background-hover);
  --button-background-active: var(--salt-actionable-positive-subtle-background-active);
  --button-borderColor: var(--salt-actionable-positive-subtle-borderColor);
  --button-borderColor-hover: var(--salt-actionable-positive-subtle-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-positive-subtle-borderColor-active);
}

.saltButton-positive.saltButton-loading {
  --button-text-color: var(--salt-actionable-positive-background);
  --button-text-color-hover: var(--salt-actionable-positive-background);
  --button-text-color-active: var(--salt-actionable-positive-background);
  --button-background: var(--salt-actionable-positive-background);
  --button-background-hover: var(--salt-actionable-positive-background);
  --button-background-active: var(--salt-actionable-positive-background);
  --button-borderColor: var(--salt-actionable-positive-borderColor);
  --button-borderColor-hover: var(--salt-actionable-positive-borderColor);
  --button-borderColor-active: var(--salt-actionable-positive-borderColor);
  cursor: var(--salt-cursor-pending);
}

.saltButton-caution.saltButton-solid {
  --button-text-color: var(--salt-actionable-caution-bold-foreground);
  --button-text-color-hover: var(--salt-actionable-caution-bold-foreground-hover);
  --button-text-color-active: var(--salt-actionable-caution-bold-foreground-active);
  --button-background: var(--salt-actionable-caution-bold-background);
  --button-background-hover: var(--salt-actionable-caution-bold-background-hover);
  --button-background-active: var(--salt-actionable-caution-bold-background-active);
  --button-borderColor: var(--salt-actionable-caution-bold-borderColor);
  --button-borderColor-hover: var(--salt-actionable-caution-bold-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-caution-bold-borderColor-active);
}

.saltButton-caution.saltButton-bordered {
  --button-text-color: var(--salt-actionable-caution-foreground);
  --button-text-color-hover: var(--salt-actionable-caution-foreground-hover);
  --button-text-color-active: var(--salt-actionable-caution-foreground-active);
  --button-background: var(--salt-actionable-caution-background);
  --button-background-hover: var(--salt-actionable-caution-background-hover);
  --button-background-active: var(--salt-actionable-caution-background-active);
  --button-borderColor: var(--salt-actionable-caution-borderColor);
  --button-borderColor-hover: var(--salt-actionable-caution-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-caution-borderColor-active);
}

.saltButton-caution.saltButton-transparent {
  --button-text-color: var(--salt-actionable-caution-subtle-foreground);
  --button-text-color-hover: var(--salt-actionable-caution-subtle-foreground-hover);
  --button-text-color-active: var(--salt-actionable-caution-subtle-foreground-active);
  --button-background: var(--salt-actionable-caution-subtle-background);
  --button-background-hover: var(--salt-actionable-caution-subtle-background-hover);
  --button-background-active: var(--salt-actionable-caution-subtle-background-active);
  --button-borderColor: var(--salt-actionable-caution-subtle-borderColor);
  --button-borderColor-hover: var(--salt-actionable-caution-subtle-borderColor-hover);
  --button-borderColor-active: var(--salt-actionable-caution-subtle-borderColor-active);
}

.saltButton-caution.saltButton-loading {
  --button-text-color: var(--salt-actionable-caution-background);
  --button-text-color-hover: var(--salt-actionable-caution-background);
  --button-text-color-active: var(--salt-actionable-caution-background);
  --button-background: var(--salt-actionable-caution-background);
  --button-background-hover: var(--salt-actionable-caution-background);
  --button-background-active: var(--salt-actionable-caution-background);
  --button-borderColor: var(--salt-actionable-caution-borderColor);
  --button-borderColor-hover: var(--salt-actionable-caution-borderColor);
  --button-borderColor-active: var(--salt-actionable-caution-borderColor);
  cursor: var(--salt-cursor-pending);
}

.saltButton strong {
  font-weight: var(--salt-text-action-fontWeight-strong);
}

.saltButton small {
  font-size: inherit;
  font-weight: var(--salt-text-action-fontWeight-small);
}

.saltButton-spinner {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.saltButton-sr-only {
  position: fixed;
  top: 0;
  left: 0;
  transform: translate(-100%, -100%);
}
`;var Hi=w(E()),Wu=({loading:e,disabled:t,focusableWhenDisabled:n,onKeyUp:r,onKeyDown:o,onClick:a,onBlur:l})=>{let[i,s]=(0,Hi.useState)(""),[c,d]=(0,Hi.useState)(!1),p="Enter",g=" ";return(0,Hi.useEffect)(()=>{let u=setTimeout(()=>{i!==p&&i!==g&&d(!1)},0);return()=>{clearTimeout(u)}},[c,i]),{active:c,buttonProps:{"aria-disabled":t&&n?!0:void 0,"data-loading":e,disabled:t&&!n,tabIndex:t&&!n?-1:0,onBlur:u=>{d(!1),l?.(u)},onClick:!e&&!t?u=>{d(!0),a?.(u)}:void 0,onKeyDown:u=>{(u.key===p||u.key===g)&&(s(u.key),d(!0)),o?.(u)},onKeyUp:u=>{s(""),d(!1),r?.(u)}}}};var _r=te("saltButton");function $P(e){switch(e){case"primary":return{appearance:"solid",sentiment:"neutral"};case"secondary":return{appearance:"transparent",sentiment:"neutral"};case"cta":return{appearance:"solid",sentiment:"accented"}}}var Ct=(0,WI.forwardRef)(function(t,n){let{className:r,props:o}=_n("saltButton",t),{children:a,disabled:l,focusableWhenDisabled:i,onKeyUp:s,onKeyDown:c,onBlur:d,onClick:p,loading:g,loadingAnnouncement:m,appearance:b,sentiment:h,type:y="button",variant:v="primary",...u}=o,{active:f,buttonProps:x}=Wu({loading:g,disabled:l,focusableWhenDisabled:i,onKeyUp:s,onKeyDown:c,onBlur:d,onClick:p}),I=Y();J({testId:"salt-button",css:zI,window:I});let C=$P(v),k=b??C?.appearance??"solid",T=h??C?.sentiment??"neutral",{tabIndex:z,...O}=x,A=y==="submit"&&g?"button":y;return(0,dl.jsxs)("button",{...O,className:V(_r(),_r(v),{[_r("loading")]:g,[_r("disabled")]:l,[_r("active")]:f,[_r(k)]:k,[_r(T)]:T},r),...u,ref:n,type:A,children:[g&&(0,dl.jsx)("div",{className:_r("spinner"),"aria-hidden":!0,children:(0,dl.jsx)(ul,{size:"small","aria-hidden":!0,disableAnnouncer:!0})}),typeof m=="string"&&(0,dl.jsx)("span",{role:"status",className:_r("sr-only"),children:m}),a]})});var uF=w(E());var fF=w(F());var ju=je("FormFieldContext",{});var jI=w(E());function gn(){return(0,jI.useContext)(ju)||{}}var $i=w(F());var wF=w(E());var VI=`.saltCheckboxIcon {
  --checkbox-size: var(--salt-size-selectable);
  width: var(--checkbox-size);
  min-width: var(--checkbox-size);
  height: var(--checkbox-size);
  min-height: var(--checkbox-size);
  border: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--salt-selectable-borderColor);
  border-radius: var(--salt-palette-corner-weaker, 0);
  color: var(--salt-selectable-foreground);
  background: var(--salt-container-primary-background);
  position: relative;
  --saltIcon-size: 100%;
  display: flex;
  /* Using overflow:hidden here causes a thin white line */
  clip-path: border-box;
  box-sizing: border-box;
}

.saltCheckboxIcon-checked,
.saltCheckbox:hover .saltCheckboxIcon-checked {
  border-color: var(--salt-selectable-borderColor-selected);
  color: var(--salt-selectable-foreground-selected);
}

.saltCheckbox:hover .saltCheckboxIcon,
.saltCheckbox:hover .saltCheckboxIcon-indeterminate {
  border-color: var(--salt-selectable-borderColor-hover);
  color: var(--salt-selectable-foreground-hover);
}

.saltCheckboxIcon-checked.saltCheckboxIcon-indeterminate {
  border-color: var(--salt-selectable-borderColor);
  color: var(--salt-selectable-foreground);
}

.saltCheckbox-disabled:hover .saltCheckboxIcon,
.saltCheckbox-disabled:hover .saltCheckboxIcon-indeterminate {
  border-color: var(--salt-selectable-borderColor);
  color: var(--salt-selectable-foreground);
}

.saltCheckbox-disabled:hover .saltCheckboxIcon-checked {
  border-color: var(--salt-selectable-borderColor-selected);
  color: var(--salt-selectable-foreground-selected);
}

.saltCheckbox-disabled:hover .saltCheckboxIcon-checked.saltCheckboxIcon-indeterminate {
  border-color: var(--salt-selectable-borderColor);
  color: var(--salt-selectable-foreground);
}

.saltCheckboxIcon-disabled,
.saltCheckbox:hover .saltCheckboxIcon-disabled,
.saltCheckboxIcon-disabled.saltCheckboxIcon-indeterminate,
.saltCheckbox:hover .saltCheckboxIcon-disabled.saltCheckboxIcon-indeterminate {
  opacity: 0.4;

  border-color: var(--salt-selectable-borderColor);
  background: var(--salt-container-primary-background);
  color: var(--salt-selectable-foreground);
}

.saltCheckboxIcon-checked.saltCheckboxIcon-disabled,
.saltCheckbox:hover .saltCheckboxIcon-checked.saltCheckboxIcon-disabled {
  border-color: var(--salt-selectable-borderColor-selected);
  color: var(--salt-selectable-foreground-selected);
}

.saltCheckboxIcon-indeterminate::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  width: calc(var(--checkbox-size) - 6px);
  height: 2px;
  background: currentColor;
  transform: translate(-50%, -50%);
}

.saltCheckboxIcon-error,
.saltCheckbox:hover .saltCheckboxIcon-error {
  color: var(--salt-status-error-foreground-decorative);
  border-color: var(--salt-status-error-borderColor);
  outline-color: var(--salt-status-error-foreground-decorative);
}

.saltCheckboxIcon-warning,
.saltCheckbox:hover .saltCheckboxIcon-warning {
  color: var(--salt-status-warning-foreground-decorative);
  border-color: var(--salt-status-warning-borderColor);
  outline-color: var(--salt-status-warning-foreground-decorative);
}

.saltCheckboxIcon-readOnly,
.saltCheckbox:hover .saltCheckboxIcon-readOnly,
.saltCheckbox-input:focus-visible + .saltCheckboxIcon-readOnly {
  border-color: var(--salt-selectable-borderColor-readonly);
  border-style: var(--salt-borderStyle-dashed);
  color: var(--salt-content-primary-foreground);
}

.saltCheckboxIcon > svg {
  position: absolute;
  /* Ensure a gap doesn't appear when device scaling is used */
  transform: scale(1.01);
}
`;var Lr=te("saltCheckboxIcon"),HI=({checked:e=!1,className:t,disabled:n,error:r,indeterminate:o,validationStatus:a,readOnly:l})=>{let i=Y();return J({testId:"salt-checkbox-icon",css:VI,window:i}),(0,$i.jsxs)("div",{"aria-hidden":"true",className:V(Lr(),{[Lr("checked")]:e,[Lr("disabled")]:n,[Lr("error")]:r,[Lr(a||"")]:a,[Lr("indeterminate")]:o,[Lr("readOnly")]:l},t),children:[e&&!o&&!l&&(0,$i.jsx)(Ai,{className:Lr("icon")}),e&&!o&&l&&(0,$i.jsx)(Bi,{className:Lr("icon")})]})};var Fn=w(F());var lr=w(E());var UP=new Set(["ArrowDown","ArrowUp","Home","End","PageUp","PageDown"]);function fl(e){return UP.has(e)}function Vu(e){return fl(e.key)?e.ctrlKey||e.metaKey?!0:e.altKey&&e.key!=="ArrowUp"&&e.key!=="ArrowDown":!1}function $I(e,t,n){switch(e){case"ArrowDown":return n.getOptionAfter(t)??n.getLastOption();case"ArrowUp":return n.getOptionBefore(t)??n.getFirstOption();case"Home":return n.getFirstOption();case"End":return n.getLastOption();case"PageUp":return n.getOptionPageAbove(t);case"PageDown":return n.getOptionPageBelow(t);default:return}}function UI(e,t,n){switch(e){case"ArrowDown":return t?n.getOptionAfter(t):n.getFirstOption();case"ArrowUp":return t?n.getOptionBefore(t):n.getLastOption();case"Home":return n.getFirstOption();case"End":return n.getLastOption();case"PageUp":{if(t)return n.getOptionPageAbove(t);let r=n.getLastOption();return r?n.getOptionPageAbove(r.data):void 0}case"PageDown":{if(t)return n.getOptionPageBelow(t);let r=n.getFirstOption();return r?n.getOptionPageBelow(r.data):void 0}default:return}}var Gv=w(F()),nC=w(E());var YP=w(E());var jF=w(F());var Oe=w(E());var LF=w(F());var Hu=w(E());function Or(e){let t=(0,Hu.useRef)(e);return ie(()=>{t.current=e},[e]),(0,Hu.useCallback)(((...n)=>{let r=t.current;return r(...n)}),[])}var KI=e=>{throw TypeError(e)},Uv=(e,t,n)=>t.has(e)||KI("Cannot "+n),Le=(e,t,n)=>(Uv(e,t,"read from private field"),n?n.call(e):t.get(e)),go=(e,t,n)=>t.has(e)?KI("Cannot add the same private member more than once"):t instanceof WeakSet?t.add(e):t.set(e,n),Ui=(e,t,n,r)=>(Uv(e,t,"write to private field"),t.set(e,n),n),Nr=(e,t,n)=>(Uv(e,t,"access private method"),n),KP=(e,t,n,r)=>({set _(o){Ui(e,t,o)},get _(){return Le(e,t,r)}}),na,ta,ar,ho,Ki,Hv,pl,An,bo,$v;function $u(e,t){return(e&t)!==0}var ml=class{constructor(t=[]){go(this,An),go(this,na,new Map),go(this,ta,new Map),go(this,ar,new Map),go(this,ho),go(this,Ki,!1),go(this,Hv,0),go(this,pl),Ui(this,pl,new Set(t))}subscribe(t,n){let r=Le(this,na).get(t);return r||(r=new Set,Le(this,na).set(t,r)),r.add(n),()=>{let o=Le(this,na).get(t);o?.delete(n),o?.size===0&&Le(this,na).delete(t)}}register(t){let n=Le(this,ta).get(t.id),r=this.getSnapshot(t.id);n&&Nr(this,An,$v).call(this,n.option.value,t.id);let o={generation:KP(this,Hv)._++,option:t};Le(this,ta).set(t.id,o);let a=Le(this,ar).get(t.value);return a===void 0?Le(this,ar).set(t.value,t.id):typeof a=="string"?Le(this,ar).set(t.value,new Set([a,t.id])):a.add(t.id),(n!==void 0||r!==this.getSnapshot(t.id))&&Nr(this,An,bo).call(this,t.id),()=>{let l=Le(this,ta).get(t.id);if(l?.generation!==o.generation)return;let i=this.getSnapshot(t.id);Le(this,ta).delete(t.id),Nr(this,An,$v).call(this,t.value,t.id),i!==0&&Nr(this,An,bo).call(this,t.id)}}getSnapshot(t,n){var r;let o=n??((r=Le(this,ta).get(t))==null?void 0:r.option);if(!o)return 0;let a=0;return t===Le(this,ho)&&(a|=1,Le(this,Ki)&&(a|=4)),Le(this,pl).has(o.value)&&(a|=2),a}setActiveId(t){if(t===Le(this,ho))return;let n=Le(this,ho);Ui(this,ho,t),n!==void 0&&Nr(this,An,bo).call(this,n),t!==void 0&&Nr(this,An,bo).call(this,t)}setFocusVisible(t){t!==Le(this,Ki)&&(Ui(this,Ki,t),Le(this,ho)!==void 0&&Nr(this,An,bo).call(this,Le(this,ho)))}setSelected(t){let n=Le(this,pl),r=new Set(t);Ui(this,pl,r);let o=new Set([...n,...r]);for(let a of o)if(n.has(a)!==r.has(a)){let l=Le(this,ar).get(a);if(typeof l=="string")Nr(this,An,bo).call(this,l);else if(l!==void 0)for(let i of l)Nr(this,An,bo).call(this,i)}}};na=new WeakMap;ta=new WeakMap;ar=new WeakMap;ho=new WeakMap;Ki=new WeakMap;Hv=new WeakMap;pl=new WeakMap;An=new WeakSet;bo=function(e){let t=Le(this,na).get(e);if(t)for(let n of[...t])n()};$v=function(e,t){let n=Le(this,ar).get(e);if(typeof n=="string"){n===t&&Le(this,ar).delete(e);return}n?.delete(t),n?.size===1?Le(this,ar).set(e,n.values().next().value):n?.size===0&&Le(this,ar).delete(e)};var GI=e=>{throw TypeError(e)},qI=(e,t,n)=>t.has(e)||GI("Cannot "+n),Re=(e,t,n)=>(qI(e,t,"read from private field"),n?n.call(e):t.get(e)),Gi=(e,t,n)=>t.has(e)?GI("Cannot add the same private member more than once"):t instanceof WeakSet?t.add(e):t.set(e,n),qi=(e,t,n,r)=>(qI(e,t,"write to private field"),t.set(e,n),n),GP=(e,t,n,r)=>({set _(o){qi(e,t,o)},get _(){return Re(e,t,r)}}),Ht,Nt,xo,Kv,ra;function YI(e,t=n=>{Promise.resolve().then(n)}){let n=!1,r=!1;return{schedule(){n||r||(n=!0,t(()=>{n=!1,r||e()}))},cancel(){r=!0,n=!1}}}var Uu=class{constructor(){Gi(this,Ht,new Map),Gi(this,Nt,[]),Gi(this,xo,new Map),Gi(this,Kv,0),Gi(this,ra,!1)}register(t,n){let r={data:t,element:n,generation:GP(this,Kv)._++};Re(this,Ht).set(t.id,r);let o=Re(this,xo).get(t.id);return o===void 0?(Re(this,xo).set(t.id,Re(this,Nt).length),Re(this,Nt).push(r)):Re(this,Nt)[o]=r,()=>{let a=Re(this,Ht).get(t.id);if(a?.generation!==r.generation)return;Re(this,Ht).delete(t.id);let l=Re(this,xo).get(t.id);l!==void 0&&Re(this,Nt)[l]===r&&(Re(this,Nt)[l]=void 0,Re(this,xo).delete(t.id),qi(this,ra,!0))}}rebuild(t){let n=[],r=new Map;for(let o of t.querySelectorAll('[role="option"]')){let a=Re(this,Ht).get(o.id);a?.element===o&&o.isConnected&&(r.set(a.data.id,n.length),n.push(a))}for(let o of Re(this,Ht).keys())r.has(o)||Re(this,Ht).delete(o);qi(this,Nt,n),qi(this,xo,r),qi(this,ra,!1)}getAt(t){if(!Re(this,ra))return Re(this,Nt)[t];let n=0;for(let r of Re(this,Nt))if(r&&Re(this,Ht).get(r.data.id)===r){if(n===t)return r;n++}}get length(){return Re(this,ra)?Re(this,Ht).size:Re(this,Nt).length}indexOfId(t){let n=Re(this,xo).get(t);if(n===void 0||!Re(this,ra))return n??-1;let r=0;for(let o=0;o<n;o++){let a=Re(this,Nt)[o];a&&Re(this,Ht).get(a.data.id)===a&&r++}return r}indexOfValue(t){let n=0;for(let r of Re(this,Nt))if(r&&Re(this,Ht).get(r.data.id)===r){if(r.data.value===t)return n;n++}return-1}findByData(t){let n=Re(this,Ht).get(t.id);return n?.data===t?n:void 0}matching(t){let n=[];for(let r of Re(this,Nt))r!==void 0&&Re(this,Ht).get(r.data.id)===r&&t(r.data)&&n.push(r);return n}snapshot(){return Re(this,Nt).filter(t=>t!==void 0)}};Ht=new WeakMap;Nt=new WeakMap;xo=new WeakMap;Kv=new WeakMap;ra=new WeakMap;function oa(e){return String(e)}function qP(e,t,n,r){var o;let a=new Intl.Collator("en",{usage:"search",sensitivity:"base"}),l=r?e.findIndex(g=>g.data.value===r.value):-1,i=r?l+1:0,s=new Map;for(let g=0;g<e.length;g++){let m=e[g].data.value;(typeof m!="number"||!Number.isNaN(m))&&!s.has(m)&&s.set(m,g)}let c=t.split(""),d=c.length>0&&c.every(g=>a.compare(g,c[0])===0),p;for(let g=0;g<e.length;g++){let m=(i+g)%e.length,b=e[m].data;if(s.get(b.value)!==m)continue;let h=n(b.value);if(a.compare(h.substring(0,t.length),t)===0)return b;p===void 0&&d&&a.compare((o=h[0])==null?void 0:o.toLowerCase(),c[0])===0&&(p=b)}return p}function Ku(e){let{open:t,defaultOpen:n,onOpenChange:r,multiselect:o,defaultSelected:a,selected:l,onSelectionChange:i,disabled:s,readOnly:c,valueToString:d=oa}=e,p=(0,Oe.useRef)(null);p.current===null&&(p.current=new ml(l??a??[]));let g=p.current,m=(0,Oe.useRef)(null),[b,h]=(0,Oe.useState)(null),y=Ee(m,h),[v,u]=(0,Oe.useState)(!1),[f,x]=(0,Oe.useState)(!1);(0,Oe.useEffect)(()=>{s&&v&&(u(!1),x(!1))},[s,v]);let[I,C]=(0,Oe.useState)(void 0),[k,T]=Ot({controlled:t,default:!!n,name:"ListControl",state:"open"}),z=(0,Oe.useRef)(void 0),O=(G,Z,se)=>{s||c||(T(G),z.current=se,G!==k&&r?.(G,Z))},[A,B]=Ot({controlled:l,default:a??[],name:"ListControl",state:"selected"}),D=Or((G,Z)=>{if(Z.disabled||c||s)return;let se=[Z.value];o&&(A.includes(Z.value)?se=A.filter($=>$!==Z.value):se=A.concat([Z.value])),B(se),i?.(G,se),o||O(!1)}),N=G=>{B([]),A.length!==0&&i?.(G,[])},R=(0,Oe.useRef)(null);R.current===null&&(R.current=new Uu);let P=R.current,j=(0,Oe.useRef)(void 0);ie(()=>{g.setActiveId(I?.id)},[I?.id,g]),ie(()=>{g.setFocusVisible(f)},[f,g]),ie(()=>{g.setSelected(A)},[g,A]);let _=(0,Oe.useCallback)((G,Z)=>{var se;let $=g.register(G),M=P.register(G,Z);return(se=j.current)==null||se.call(j),()=>{var X;M(),$(),(X=j.current)==null||X.call(j)}},[g,P]);(0,Oe.useEffect)(()=>{if(!b)return;let G=()=>{$.takeRecords(),P.rebuild(b)},Z=YI(G);j.current=Z.schedule;let se=M=>M.nodeType===Node.ELEMENT_NODE&&(M.matches('[role="option"]')||M.querySelector('[role="option"]')!==null),$=new MutationObserver(M=>{M.some(({addedNodes:X,removedNodes:he})=>Array.from(X).some(se)||Array.from(he).some(se))&&Z.schedule()});return $.observe(b,{childList:!0,subtree:!0}),G(),()=>{j.current=void 0,Z.cancel(),$.disconnect()}},[b,P]);let W=(0,Oe.useCallback)(G=>P.getAt(G),[P]),ee=(0,Oe.useCallback)(G=>P.indexOfValue(G.value),[P]),ne=(0,Oe.useCallback)(G=>P.matching(G),[P]),de=(0,Oe.useCallback)((G,Z)=>qP(P.snapshot(),G,d,Z),[P,d]),U=(0,Oe.useCallback)(()=>W(0),[W]),me=(0,Oe.useCallback)(()=>W(P.length-1),[W,P]),ce=(0,Oe.useCallback)(G=>{let Z=P.indexOfId(G.id);return W(Z-1)},[W,P]),be=(0,Oe.useCallback)(G=>{let Z=P.indexOfId(G.id);return W(Z+1)},[W,P]),fe=(0,Oe.useCallback)(G=>{var Z;let se=m.current,$=P.findByData(G);if(!se||!$)return;let M=se.getBoundingClientRect(),X=$.element.getBoundingClientRect(),he=M.y-se.scrollTop,Se=Math.max(0,X.y-he+X.height-M.height);for(;$&&X&&X.y-he>Se;)$=ce($.data),X=(Z=$?.element)==null?void 0:Z.getBoundingClientRect();return $??U()},[U,ce,P]),re=(0,Oe.useCallback)(G=>{let Z=m.current,se=P.findByData(G);if(!Z||!se)return;let $=Z.getBoundingClientRect(),M=se.element.getBoundingClientRect(),X=$.y-Z.scrollTop,he=Math.min(Z.scrollHeight,M.y-X-M.height+$.height);for(;se&&M&&M.y-X<he;)se=be(se.data),M=se?.element.getBoundingClientRect();return se??me()},[me,be,P]);return(0,Oe.useEffect)(()=>{var G;if(m.current){let Z=I?(G=P.findByData(I))==null?void 0:G.element:void 0;if(!Z)return;Z.scrollIntoView({block:"nearest",inline:"nearest"})}},[I,P]),{multiselect:!!o,openState:k,setOpen:O,openKey:z,activeState:I,setActive:C,selectedState:A,setSelectedState:B,select:D,clear:N,focusVisibleState:f,setFocusVisibleState:x,focusedState:v,setFocusedState:u,setListRef:y,listRef:m,register:_,getOptionAtIndex:W,getIndexOfOption:ee,getOptionsMatching:ne,getOptionFromSearch:de,getOptionAfter:be,getOptionBefore:ce,getOptionPageAbove:fe,getOptionPageBelow:re,getFirstOption:U,getLastOption:me,valueToString:d,disabled:s,optionStateStore:g}}var QI=je("ListControlContext",{openState:!1,setOpen(){},register(){return()=>{}},selectedState:[],select(){},activeState:void 0,setActive(){},multiselect:!1,focusVisibleState:!1,valueToString:oa,disabled:!1,listRef:void 0});var XI=w(F()),ZI=w(E());var QP=new ml,XP={disabled:!1,listRef:void 0,multiselect:!1,optionStateStore:QP,register:()=>()=>{},select:()=>{},setActive:()=>{},valueToString:e=>String(e)},JI=je("ListControlOptionContext",XP);function eC({children:e,value:t}){return(0,XI.jsx)(JI.Provider,{value:t,children:e})}function tC(){return(0,ZI.useContext)(JI)}function Gu({children:e,value:t}){let{optionStateStore:n,...r}=t,o=(0,nC.useMemo)(()=>({disabled:t.disabled,listRef:t.listRef,multiselect:t.multiselect,optionStateStore:n,register:t.register,select:t.select,setActive:t.setActive,valueToString:t.valueToString}),[n,t.disabled,t.listRef,t.multiselect,t.register,t.select,t.setActive,t.valueToString]);return(0,Gv.jsx)(QI.Provider,{value:r,children:(0,Gv.jsx)(eC,{value:o,children:e})})}var qv=w(F());var sC=w(E());var oC=w(F());var aC=w(E());var rC=`.saltOptionList {
  background: var(--salt-container-primary-background);
  border: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--salt-selectable-borderColor-selected);
  border-radius: var(--salt-palette-corner, 0);
  overflow: hidden;
  overflow-y: auto;
  position: relative;
  z-index: var(--salt-zIndex-flyover);
  box-shadow: var(--salt-overlayable-shadow-popout);
  box-sizing: border-box;
  max-height: var(--overlay-maxHeight);
  min-width: var(--overlay-minWidth);
}

.saltOptionList-container {
  display: flex;
  flex-direction: column;
  gap: var(--salt-spacing-fixed-100);
  max-height: inherit;
  min-height: inherit;
}

.saltOptionList-collapsed {
  display: none;
}
`;var ZP=te("saltOptionList"),lC=(0,aC.forwardRef)(function(t,n){let{children:r,className:o,...a}=t,l=Y();return J({testId:"salt-option-list",css:rC,window:l}),(0,oC.jsx)("div",{className:V(ZP("container"),o),...a,ref:n,children:r})});var iC=te("saltOptionList"),qu=(0,sC.forwardRef)(function(t,n){let{children:r,className:o,collapsed:a,open:l,...i}=t,{Component:s}=Eu();return(0,qv.jsx)(s,{className:V(iC(),{[iC("collapsed")]:a},o),role:"listbox",open:l,...i,ref:n,children:(0,qv.jsx)(lC,{children:r})})});var vt=w(F());var yo=w(E());var Qu=w(F());var aa=w(E());var cC=`/* Styles applied to the root element */
.saltPill {
  --pill-borderWidth: var(--salt-size-fixed-100);

  appearance: none;
  display: inline-flex;
  align-items: center;
  background: var(--saltPill-background, var(--pill-background));
  border-radius: var(--salt-palette-corner-weaker, 0);
  border-style: solid;
  border-width: var(--pill-borderWidth);
  border-color: var(--pill-borderColor);
  height: calc(var(--salt-size-base) - var(--salt-spacing-100));
  min-height: var(--salt-text-minHeight);
  position: relative;
  gap: var(--salt-spacing-50);
  padding: 0 calc(var(--salt-spacing-50) - var(--pill-borderWidth));
  color: var(--saltPill-color, var(--pill-color));
  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-fontWeight);
  line-height: var(--salt-text-lineHeight);
  letter-spacing: var(--salt-text-letterSpacing);
  overflow: hidden;
  white-space: nowrap;
}

/* Style applied to Pill if pill is clickable  */
.saltPill-clickable {
  --pill-background: var(--salt-actionable-bold-background);
  --pill-color: var(--salt-actionable-bold-foreground);
  --pill-borderColor: var(--salt-actionable-bold-borderColor);
  cursor: var(--salt-cursor-hover);
}

.saltPill-clickable:hover,
.saltPill-clickable:focus-visible {
  --pill-color: var(--salt-actionable-bold-foreground-hover);
  --pill-background: var(--salt-actionable-bold-background-hover);
  --pill-borderColor: var(--salt-actionable-bold-borderColor-hover);
}

.saltPill-clickable.saltPill-active,
.saltPill-clickable:active {
  --pill-color: var(--salt-actionable-bold-foreground-active);
  --pill-background: var(--salt-actionable-bold-background-active);
  --pill-borderColor: var(--salt-actionable-bold-borderColor-active);
}

/* Style applied to Pill on focus */
.saltPill:focus-visible {
  outline: var(--salt-focused-outline);
}

/* Styles applied when the pill triggers a menu */
.saltPill[aria-expanded="true"][aria-haspopup="menu"] {
  --pill-color: var(--salt-actionable-bold-foreground-active);
  --pill-background: var(--salt-actionable-bold-background-active);
  --pill-borderColor: var(--salt-actionable-bold-borderColor-active);
}

/* Style applied to Pill when disabled */
.saltPill:disabled,
.saltPill:disabled:hover {
  --pill-color: var(--salt-actionable-bold-foreground);
  --pill-background: var(--salt-actionable-bold-background);
  --pill-borderColor: var(--salt-actionable-bold-borderColor);
  cursor: var(--salt-cursor-disabled);

  opacity: 0.4;
}
`;var Yu=w(F());var vM=w(E());var uC=`.saltPillCheckIcon {
  --checkbox-size: var(--salt-size-selectable);
  width: var(--checkbox-size);
  min-width: var(--checkbox-size);
  height: var(--checkbox-size);
  min-height: var(--checkbox-size);
  border: var(--salt-size-fixed-100) var(--salt-borderStyle-solid);
  border-radius: var(--salt-palette-corner-weaker, 0);
  position: relative;
  --saltIcon-size: 100%;
  display: flex;
  pointer-events: none;
  /* Using overflow:hidden here causes a thin white line */
  clip-path: border-box;
  box-sizing: border-box;
}

.saltPillCheckIcon > svg {
  pointer-events: none;
  position: absolute;
  /* Ensure a gap doesn't appear when device scaling is used */
  transform: scale(1.01);
}
`;var vl=te("saltPillCheckIcon"),dC=({className:e,checked:t=!1,disabled:n=!1,active:r=!1})=>{let o=Y();return J({testId:"salt-pill-check-icon",css:uC,window:o}),(0,Yu.jsx)("div",{"aria-hidden":"true",className:V(vl(),{[vl("checked")]:t,[vl("disabled")]:n,[vl("active")]:r},e),children:t&&(r?(0,Yu.jsx)(Bi,{className:vl("icon")}):(0,Yu.jsx)(Ai,{className:vl("solidIcon")}))})};var fC=w(E());var wM=w(F());var JP=je("PillGroupContext",{selected:[],select:()=>{},selectionVariant:"none"});function pC(){return(0,fC.useContext)(JP)}var Yv=te("saltPill"),mC=(0,aa.forwardRef)(function({children:t,className:n,disabled:r,onKeyUp:o,onKeyDown:a,onClick:l,onBlur:i,onPointerDown:s,value:c,...d},p){let[g,m]=(0,aa.useState)(!1),[b,h]=(0,aa.useState)(!1),y=pC(),v=Y();J({testId:"salt-pill",css:cC,window:v});let u=y.selectionVariant==="multiple",f=P=>{u&&c&&y.select(P,c),l?.(P)},x=P=>{s?.(P),!r&&m(!0)},I=P=>{if(a?.(P),P.key==="Enter"&&u){P.preventDefault();return}P.key===" "&&u&&h(!0)},C=P=>{o?.(P),u&&P.key===" "&&h(!1)};(0,aa.useEffect)(()=>{if(!v)return;let P=()=>m(!1);return v.addEventListener("pointerup",P),v.addEventListener("pointercancel",P),()=>{v.removeEventListener("pointerup",P),v.removeEventListener("pointercancel",P)}},[v]);let{buttonProps:k,active:T}=Wu({disabled:r,onKeyUp:C,onKeyDown:I,onClick:f,onBlur:i}),{tabIndex:z,disabled:O,...A}=k,B=!!c&&u&&y.selected.includes(c),D=y.disabled||O,N=u?g||b:g||T,R=u?{"aria-checked":B,role:"checkbox",value:c}:{};return(0,Qu.jsxs)("button",{"data-testid":"pill",ref:p,className:V(Yv(),Yv("clickable"),{[Yv("active")]:N},n),type:"button",onPointerDown:x,disabled:D,...A,...R,...d,children:[u&&(0,Qu.jsx)(dC,{checked:B,active:N}),t]})});var hC=w(F());var bC=w(E());var vC=`.saltStatusAdornment {
  align-self: center;
  display: inline-block;
  fill: var(--saltStatusAdornment-color, var(--statusAdornment-color));
  height: var(--salt-size-adornment);
  min-height: var(--salt-size-adornment);
  padding-left: var(--salt-spacing-100);
  position: relative;
}

.saltStatusAdornment-error {
  --statusAdornment-color: var(--salt-status-error-foreground-decorative);
}

.saltStatusAdornment-warning {
  --statusAdornment-color: var(--salt-status-warning-foreground-decorative);
}

.saltStatusAdornment-success {
  --statusAdornment-color: var(--salt-status-success-foreground-decorative);
}
`;var gC=te("saltStatusAdornment"),gl=(0,bC.forwardRef)(function({className:t,status:n,...r},o){let a=vn(),i=`${or(n)}StatusAdornment`,s=a[i],c=n,d=Y();return J({testId:"salt-status-adornment",css:vC,window:d}),s===void 0?null:(0,hC.jsx)(s,{className:V(gC(),gC(n),t),"aria-label":c,...r,ref:o})});var xC=`/* Style applied to the root element */
.saltPillInput {
  align-items: center;
  background: var(--saltPillInput-background, var(--pillInput-background));
  border-radius: var(--salt-palette-corner-weak, 0);
  color: var(--saltPillInput-color, var(--salt-content-primary-foreground));
  display: inline-flex;
  font-family: var(--salt-text-fontFamily);
  font-size: var(--saltPillInput-fontSize, var(--salt-text-fontSize));
  line-height: var(--saltPillInput-lineHeight, var(--salt-text-lineHeight));
  letter-spacing: var(--salt-text-letterSpacing);
  min-height: var(--saltPillInput-minHeight, var(--salt-size-base));
  min-width: var(--saltPillInput-minWidth, 4em);
  padding-left: var(--saltPillInput-paddingLeft, var(--salt-spacing-100));
  padding-right: var(--saltPillInput-paddingRight, var(--salt-spacing-100));
  position: relative;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.saltPillInput-truncate {
  height: var(--salt-size-base);
}

.saltPillInput-truncate .saltPillInput-inputWrapper {
  flex-wrap: nowrap;
}

.saltPillInput:hover {
  cursor: var(--salt-cursor-text);
}

/* Style applied if \`bordered={true}\` */
.saltPillInput-bordered.saltPillInput {
  --pillInput-borderWidth: var(--salt-size-fixed-100);
  border: var(--pillInput-borderWidth) var(--salt-borderStyle-solid) var(--pillInput-borderColor);
}

.saltPillInput-bordered.saltPillInput:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--pillInput-borderColor-hover);
}

/* Style applied if focused or active when \`bordered={true}\` */
.saltPillInput-bordered.saltPillInput-focused,
.saltPillInput-bordered.saltPillInput-focused:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--pillInput-borderColor-active);
}

.saltPillInput-bordered.saltPillInput-readOnly,
.saltPillInput-bordered.saltPillInput-readOnly:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--salt-editable-borderColor-readonly);
}

.saltPillInput-bordered.saltPillInput-disabled,
.saltPillInput-bordered.saltPillInput-disabled:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--salt-editable-borderColor-disabled);
}

.saltPillInput-activationIndicator {
  left: 0;
  bottom: 0;
  width: 100%;
  position: absolute;
  border-bottom: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--pillInput-borderColor);
}

.saltPillInput:hover .saltPillInput-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--pillInput-borderColor-hover);
}

.saltPillInput-focused .saltPillInput-activationIndicator,
.saltPillInput-focused:hover .saltPillInput-activationIndicator {
  border-bottom: var(--salt-size-fixed-200) var(--salt-borderStyle-solid) var(--pillInput-borderColor-active);
}

.saltPillInput-readOnly .saltPillInput-activationIndicator,
.saltPillInput-readOnly:hover .saltPillInput-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--salt-editable-borderColor-readonly);
}

.saltPillInput-disabled .saltPillInput-activationIndicator,
.saltPillInput-disabled:hover .saltPillInput-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--salt-editable-borderColor-disabled);
}

.saltPillInput-bordered .saltPillInput-activationIndicator,
.saltPillInput-bordered.saltPillInput-readOnly .saltPillInput-activationIndicator,
.saltPillInput-bordered.saltPillInput-disabled:hover .saltPillInput-activationIndicator {
  border-bottom-width: 0;
}

.saltPillInput-bordered.saltPillInput-focused .saltPillInput-activationIndicator {
  border-bottom-width: calc(var(--salt-size-fixed-200) - var(--pillInput-borderWidth));
}

/* Class applied if \`variant="primary"\` */
.saltPillInput-primary {
  --pillInput-background: var(--salt-editable-primary-background);
  --pillInput-background-disabled: var(--salt-editable-primary-background-disabled);
  --pillInput-background-readonly: var(--salt-editable-background-readonly);
  --pillInput-borderColor: var(--salt-editable-borderColor);
  --pillInput-borderColor-active: var(--salt-editable-borderColor-active);
  --pillInput-borderColor-hover: var(--salt-editable-borderColor-hover);
  --pillInput-outlineColor: var(--salt-focused-outlineColor);
}

/* Class applied if \`variant="secondary"\` */
.saltPillInput-secondary {
  --pillInput-background: var(--salt-editable-secondary-background);
  --pillInput-background-disabled: var(--salt-editable-secondary-background-disabled);
  --pillInput-background-readonly: var(--salt-editable-background-readonly);
  --pillInput-borderColor: var(--salt-editable-borderColor);
  --pillInput-borderColor-active: var(--salt-editable-borderColor-active);
  --pillInput-borderColor-hover: var(--salt-editable-borderColor-hover);
  --pillInput-outlineColor: var(--salt-focused-outlineColor);
}

/* Class applied if \`variant="tertiary"\` */
.saltPillInput-tertiary {
  --pillInput-background: var(--salt-editable-tertiary-background);
  --pillInput-background-readonly: var(--salt-editable-background-readonly);
  --pillInput-borderColor: var(--salt-editable-borderColor);
  --pillInput-borderColor-active: var(--salt-editable-borderColor-active);
  --pillInput-borderColor-hover: var(--salt-editable-borderColor-hover);
  --pillInput-outlineColor: var(--salt-focused-outlineColor);
}

/* Style applied to input if \`validationState="error"\` */
.saltPillInput-error {
  --pillInput-background: var(--salt-status-error-background);
  --pillInput-background-readonly: var(--salt-status-error-background);
  --pillInput-borderColor: var(--salt-status-error-borderColor);
  --pillInput-borderColor-active: var(--salt-status-error-borderColor);
  --pillInput-borderColor-hover: var(--salt-status-error-borderColor);
  --pillInput-outlineColor: var(--salt-status-error-borderColor);
}

/* Style applied to input if \`validationState="warning"\` */
.saltPillInput-warning {
  --pillInput-background: var(--salt-status-warning-background);
  --pillInput-background-readonly: var(--salt-status-warning-background);
  --pillInput-borderColor: var(--salt-status-warning-borderColor);
  --pillInput-borderColor-active: var(--salt-status-warning-borderColor);
  --pillInput-borderColor-hover: var(--salt-status-warning-borderColor);
  --pillInput-outlineColor: var(--salt-status-warning-borderColor);
}

/* Style applied to input if \`validationState="success"\` */
.saltPillInput-success {
  --pillInput-background: var(--salt-status-success-background);
  --pillInput-background-readonly: var(--salt-status-success-background);
  --pillInput-borderColor: var(--salt-status-success-borderColor);
  --pillInput-borderColor-active: var(--salt-status-success-borderColor);
  --pillInput-borderColor-hover: var(--salt-status-success-borderColor);
  --pillInput-outlineColor: var(--salt-status-success-borderColor);
}

/* Styling when focused */
.saltPillInput-focused,
.saltPillInput-focused:hover {
  cursor: var(--salt-cursor-text);
  outline: var(--saltPillInput-outline, var(--salt-focused-outlineWidth) var(--salt-focused-outlineStyle) var(--pillInput-outlineColor));
}

/* Style applied if \`readOnly={true}\` */
.saltPillInput.saltPillInput-readOnly {
  background: var(--pillInput-background-readonly);
  cursor: var(--salt-cursor-readonly);
}

/* Styling when focused if \`disabled={true}\` */
.saltPillInput-disabled,
.saltPillInput-disabled:hover {
  background: var(--pillInput-background-disabled);
  cursor: var(--salt-cursor-disabled);
  color: var(--saltPillInput-color-disabled, var(--salt-content-primary-foreground-disabled));
}

/* Style applied to start adornments */
.saltPillInput-startAdornmentContainer {
  align-items: center;
  display: inline-flex;
  padding-right: var(--salt-spacing-100);
  column-gap: var(--salt-spacing-100);
}

/* Style applied to end adornments */
.saltPillInput-endAdornmentContainer {
  align-items: center;
  display: inline-flex;
  padding-left: var(--salt-spacing-50);
  padding-top: var(--salt-spacing-50);
  column-gap: var(--salt-spacing-100);
  align-self: flex-start;
}

.saltPillInput-statusAdornmentContainer {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  height: var(--salt-size-base);
}

.saltPillInput-readOnly .saltPillInput-startAdornmentContainer {
  margin-left: var(--salt-spacing-50);
}

.saltPillInput-startAdornmentContainer .saltButton ~ .saltButton {
  margin-left: calc(-1 * var(--salt-spacing-50));
}

.saltPillInput-endAdornmentContainer .saltButton ~ .saltButton {
  margin-left: calc(-1 * var(--salt-spacing-50));
}

.saltPillInput-startAdornmentContainer .saltButton:first-child {
  margin-left: calc(var(--salt-spacing-50) * -1);
}

.saltPillInput-endAdornmentContainer .saltButton:last-child {
  margin-right: calc(var(--salt-spacing-50) * -1);
}

.saltPillInput-startAdornmentContainer > .saltButton,
.saltPillInput-endAdornmentContainer > .saltButton {
  --saltButton-padding: calc(var(--salt-spacing-50) - var(--button-borderWidth));
  --saltButton-height: calc(var(--salt-size-base) - var(--salt-spacing-100));
  --saltButton-borderRadius: var(--salt-palette-corner-weaker);
}

.saltPillInput-inputWrapper {
  display: flex;
  gap: var(--salt-spacing-50);
  align-items: center;
  flex: 1;
  padding: var(--salt-spacing-50) 0;
  flex-wrap: wrap;
  max-height: inherit;
  height: inherit;
  overflow-y: auto;
  box-sizing: border-box;
}

.saltPillInput-bordered > .saltPillInput-endAdornmentContainer {
  padding-top: calc(var(--salt-spacing-50) - var(--pillInput-borderWidth));
}

.saltPillInput-bordered > .saltPillInput-inputWrapper {
  padding: calc(var(--salt-spacing-50) - var(--pillInput-borderWidth)) 0;
}

.saltPillInput-pillList {
  display: contents;
}

.saltPillInput-pillList div[role="listitem"] {
  display: inline;
}

.saltPillInput-overflowIndicator {
  width: calc(var(--salt-size-base) - var(--salt-spacing-100));
  height: calc(var(--salt-size-base) - var(--salt-spacing-100));
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Style applied to inner input component */
.saltPillInput-input {
  background: none;
  border: none;
  box-sizing: content-box;
  color: inherit;
  cursor: inherit;
  display: block;
  flex: 1;
  font: inherit;
  height: 100%;
  letter-spacing: var(--saltPillInput-letterSpacing, var(--salt-text-letterSpacing));
  margin: 0;
  min-width: 0;
  overflow: hidden;
  padding: 0;
  text-align: var(--pillInput-textAlign, left);
  width: 100%;
}

/* Reset in the  class */
.saltPillInput-input:focus {
  outline: none;
}

/* Style applied to selected input if \`disabled={true}\` */
.saltPillInput-disabled .saltPillInput-input::selection {
  background: none;
}

/* Style applied to placeholder text */
.saltPillInput-input::placeholder {
  color: var(--salt-content-secondary-foreground);
  font-weight: var(--salt-text-fontWeight-small);
}
`;var Ju=w(E());var ZM=w(F());var yC=w(E());function Xu(e){return e?.ownerDocument||document}function Br(e){return Xu(e).defaultView||window}function wC({ref:e,onResize:t}){(0,yC.useEffect)(()=>{let n=e?.current;if(!n)return;let r=Br(n),o=new r.ResizeObserver(a=>{requestAnimationFrame(()=>{a.length!==0&&t()})});return o.observe(n),()=>{n&&o.unobserve(n)}},[e,t])}var Zu=w(E());function IC(e){let[t,n]=(0,Zu.useState)(e),r=(0,Zu.useRef)(null),o=Or(()=>{if(!r.current)return;let l=r.current.next();if(l.done){r.current=null;return}t===l.value?o():n(l.value)});ie(()=>{r.current&&o()});let a=Or(l=>{r.current=l(t),o()});return[t,a]}function CC({pills:e,enable:t}){let n=(0,Ju.useRef)(null),[r,o]=IC(e.length),a=Y(),l=(0,Ju.useCallback)(()=>{if(!t)return;let i=s=>{let c=n.current;if(c&&a){let d=Array.from(c.querySelectorAll('[role="listitem"]')),p=c.getBoundingClientRect().width,g=Number.parseInt(a.getComputedStyle(c).gap,10),m=c.querySelector("[data-overflowindicator]"),b=0,h=0;if(m){let y=d.pop();if(y){let v=y.getBoundingClientRect().width;b+=v+g}}for(let y of d){let v=y.getBoundingClientRect().width;if(b+=v+g,Math.round(b)<=Math.round(p))h++;else break}return h}return s};o(function*(){yield e.length;let s=i(e.length),c=s<e.length&&s>0;yield s,c&&(yield i(s))})},[e,o,t,a]);return ie(()=>{l()},[l]),wC({ref:n,onResize:l}),{pillListRef:n,visibleCount:r,visiblePills:t?e.slice(0,r):e}}var St=te("saltPillInput");function SC(e){return e==null||e===""||Array.isArray(e)&&e.length===0}var kC=(0,yo.forwardRef)(function({"aria-activedescendant":t,"aria-expanded":n,"aria-owns":r,className:o,disabled:a,emptyReadOnlyMarker:l="\u2014",endAdornment:i,hidePillClose:s,id:c,inputProps:d={},inputRef:p,name:g,placeholder:m,pills:b=[],onPillRemove:h,readOnly:y,role:v,startAdornment:u,style:f,textAlign:x="left",value:I,defaultValue:C=I===void 0?"":void 0,validationStatus:k,variant:T="primary",truncate:z,bordered:O=!1,...A},B){let D=Y(),{OverflowIcon:N,CloseIcon:R}=vn();J({testId:"salt-pill-input",css:xC,window:D});let{a11yProps:{"aria-describedby":P,"aria-labelledby":j}={},disabled:_,readOnly:W,necessity:ee,validationStatus:ne}=gn(),de={"aria-activedescendant":t,"aria-expanded":n,"aria-owns":r},U=a||_,me=y||W,ce=ne??k,[be,fe]=(0,yo.useState)(!1),[re,G]=(0,yo.useState)(-1),Z=me&&SC(I),se=me&&SC(C),$=I===void 0?void 0:Z?l:I,M=se?l:C,{"aria-describedby":X,"aria-labelledby":he,onBlur:Se,onFocus:ge,onChange:ve,required:we,onKeyDown:ye,..._e}=d,L=ee?["required","asterisk"].includes(ee):we,[K,oe]=Ot({controlled:$,default:M,name:"Input",state:"value"}),{visiblePills:pe,pillListRef:Je}=CC({pills:b,enable:z&&b.length>0}),Hn=We(c),_o=`${Hn}-optionsList`,rn=(0,yo.useRef)([]),dr=(0,yo.useRef)(null),da=Ee(dr,p),Lo=ke=>{let $e=ke.target.value;oe($e),ve?.(ke)},Dr=ke=>{var $e;let Rt=ke.currentTarget;if(Rt.selectionStart===0&&Rt.selectionEnd===0){let Ft=b.length-1,fr=b[Ft];ke.key==="Backspace"&&fr?(ke.preventDefault(),h?.(ke,Ft)):ke.key==="ArrowLeft"&&(ke.preventDefault(),($e=rn.current[Ft])==null||$e.focus())}ye?.(ke)},Cl=ke=>{var $e,Rt,Ft,fr,fa,pa;let zr=ke.currentTarget,on=Number(zr.dataset.index);ke.key==="ArrowLeft"?(ke.preventDefault(),($e=rn.current[on-1])==null||$e.focus()):ke.key==="ArrowRight"?(ke.preventDefault(),on===b.length-1?(Rt=dr?.current)==null||Rt.focus():(Ft=rn.current[on+1])==null||Ft.focus()):(ke.key==="Delete"||ke.key==="Backspace")&&(ke.preventDefault(),h?.(ke,on),b.length===1?(fr=dr.current)==null||fr.focus():on===b.length-1?(fa=rn.current[b.length-2])==null||fa.focus():(pa=rn.current[on])==null||pa.focus())},Sl=ke=>{var $e;if(!s){let Rt=ke.currentTarget,Ft=Number(Rt.dataset.index);h?.(ke,Ft)}($e=dr.current)==null||$e.focus()},kl=ke=>{Se?.(ke),fe(!1)},Oo=ke=>{ge?.(ke),fe(!0)},Tl={"--input-textAlign":x,...f};return(0,vt.jsxs)("div",{className:V(St(),St(T),{[St("focused")]:!U&&be,[St("disabled")]:U,[St("readOnly")]:me,[St("truncate")]:z,[St(ce??"")]:ce,[St("bordered")]:O},o),ref:B,style:Tl,...A,children:[u&&(0,vt.jsx)("div",{className:St("startAdornmentContainer"),children:u}),(0,vt.jsxs)("div",{className:St("inputWrapper"),ref:Je,children:[(0,vt.jsxs)("div",{role:"list",className:St("pillList"),"aria-labelledby":V(j,_o),"aria-label":"Selected Options",id:_o,children:[pe?.map((ke,$e)=>(0,vt.jsx)("div",{role:"listitem",children:(0,vt.jsxs)(mC,{"data-index":$e,disabled:U,"aria-label":s?ke:`Remove ${ke}`,ref:Rt=>{Rt?rn.current[$e]=Rt:rn.current=rn.current.filter(Ft=>Ft!==Rt)},onFocus:()=>G($e),onKeyDown:Cl,onClick:Sl,tabIndex:$e===(re>=0&&re<pe.length?re:0)?0:-1,children:[ke,!s&&(0,vt.jsx)(R,{"aria-hidden":!0})]})},ke)),pe.length<b.length&&(0,vt.jsx)("div",{role:"listitem",children:(0,vt.jsx)("div",{"data-overflowindicator":!0,className:St("overflowIndicator"),children:(0,vt.jsx)(N,{"aria-hidden":!0})})})]}),(0,vt.jsx)("input",{"aria-describedby":V(P,X)||void 0,"aria-labelledby":V(j,he)||void 0,autoComplete:"off",className:V(St("input"),d?.className),disabled:U,id:Hn,name:g,readOnly:me,ref:da,role:v,tabIndex:U?-1:0,onBlur:kl,onChange:Lo,onFocus:U?void 0:Oo,onKeyDown:Dr,placeholder:m,value:K,...de,..._e,required:L})]}),!U&&ce&&(0,vt.jsx)("div",{className:St("statusAdornmentContainer"),children:(0,vt.jsx)(gl,{status:ce})}),i&&(0,vt.jsx)("div",{className:St("endAdornmentContainer"),children:i}),(0,vt.jsx)("div",{className:St("activationIndicator")})]})});var bD=w(E());var yD=w(F());function TC(e){let{open:t,defaultOpen:n,onOpenChange:r,multiselect:o,defaultSelected:a,selected:l,onSelectionChange:i,disabled:s,readOnly:c,valueToString:d,value:p,defaultValue:g}=e,m=Ku({open:t,defaultOpen:n,onOpenChange:r,multiselect:o,defaultSelected:a,selected:l,onSelectionChange:i,disabled:s,readOnly:c,valueToString:d}),{selectedState:b,setSelectedState:h,setOpen:y}=m,[v,u]=Ot({controlled:p,default:g??(b.length===1&&!o?m.valueToString(b[0]):g),name:"ComboBox",state:"value"}),f=Or((I,C)=>{if(C.disabled||s||c)return;let k=[C.value];o&&(b.includes(C.value)?k=b.filter(T=>T!==C.value):k=b.concat([C.value])),h(k),u(o?"":m.valueToString(C.value)),i?.(I,k),o||y(!1)});return{...m,select:f,valueState:v,setValueState:u,removePill:(I,C)=>{if(!o||s||c)return;let k;b.includes(C)?k=b.filter(T=>T!==C):k=b.concat([C]),h(k),u(""),i?.(I,k)}}}var Qv=te("saltComboBox"),Xv=(0,lr.forwardRef)(function(t,n){var r,o;let{className:a,props:l}=_n("saltComboBox",t),{children:i,disabled:s,endAdornment:c,readOnly:d,multiselect:p,selectOnTab:g=!p,onSelectionChange:m,selected:b,defaultSelected:h,defaultOpen:y,onOpenChange:v,onChange:u,open:f,inputRef:x,inputProps:I,variant:C="primary",onKeyDown:k,onFocus:T,onBlur:z,value:O,defaultValue:A,valueToString:B=oa,truncate:D,bordered:N=!1,OverlayProps:R,...P}=l,{CollapseIcon:j,ExpandIcon:_}=vn(),{a11yProps:{"aria-labelledby":W}={},disabled:ee,readOnly:ne}=gn(),de=!!s||ee,U=!!d||ne,me=(0,lr.useRef)(null),ce=Ee(me,x),be=(0,lr.useRef)(!1),fe=TC({open:f,defaultOpen:y,onOpenChange:v,multiselect:p,defaultSelected:h,selected:b,onSelectionChange:m,value:O,defaultValue:A,disabled:de,readOnly:U,valueToString:B}),{activeState:re,setActive:G,openState:Z,setOpen:se,openKey:$,getOptionsMatching:M,getFirstOption:X,getLastOption:he,getOptionAfter:Se,getOptionBefore:ge,getOptionPageAbove:ve,getOptionPageBelow:we,selectedState:ye,select:_e,clear:L,focusVisibleState:K,setFocusVisibleState:oe,focusedState:pe,setFocusedState:Je,listRef:Hn,setListRef:_o,valueState:rn,setValueState:dr,removePill:da}=fe,Lo=(le,ut,an)=>{var qg;let ek=an==="focus"&&le;an==="focus"&&Je(le),an==="focus"&&!le&&oe(!1),!(U||ek)&&(se(le),le&&((qg=me.current)==null||qg.focus()))},Dr=lr.Children.toArray(i).filter(Boolean).length>0,{x:Cl,y:Sl,strategy:kl,elements:Oo,floating:Tl,reference:ke,context:$e}=sl({open:Z&&!U&&Dr,onOpenChange:Lo,placement:"bottom-start",strategy:"fixed",middleware:[uo(1),Zo({apply({rects:le,elements:ut,availableHeight:an}){ut.floating.style.setProperty("--overlay-minWidth",`${le.reference.width}px`),ut.floating.style.setProperty("--overlay-maxHeight",`max(calc((var(--salt-size-base) + var(--salt-spacing-100)) * 5), calc(${an}px - var(--salt-spacing-100)))`)}}),kr({fallbackStrategy:"initialPlacement"})]}),{getReferenceProps:Rt,getFloatingProps:Ft}=rl([nl($e),bu($e),tl($e,{keyboardHandlers:!1,toggle:!1})]),fr=Ee(ke,n),fa=le=>{U||(le.stopPropagation(),oe(!1),se(!Z,"manual"))},pa=()=>{var le;(le=me.current)==null||le.focus()},zr=le=>{if(k?.(le),le.repeat||(be.current=!1),U||Vu(le))return;if(!Z&&(le.key==="ArrowDown"||le.key==="ArrowUp")){se(!0,void 0,le.key);return}if((!Z||!Dr)&&fl(le.key))return;let ut=re;(le.key==="PageUp"||le.key==="PageDown")&&le.preventDefault();let an=UI(le.key,ut,{getFirstOption:X,getLastOption:he,getOptionAfter:Se,getOptionBefore:ge,getOptionPageAbove:ve,getOptionPageBelow:we});switch(le.key){case"Enter":if(Z&&re?.disabled){le.preventDefault();return}if(!Z||!re)return;_e(le,re),p||le.preventDefault();break;case"Tab":Z&&g&&re&&!re?.disabled&&!ye.includes(re?.value)&&_e(le,re);break}an&&oe(!0),an&&an.data.id!==re?.id&&(le.preventDefault(),G(an.data))},on=le=>{le.currentTarget===me.current?Je(!0):G(void 0),T?.(le)},Rd=le=>{le.persist(),(!Hn.current||!Hn.current.contains(le.relatedTarget))&&(z?.(le),be.current=!1)},Ed=le=>{let ut=le.target.value;Z||se(!0,"input"),ut===""&&!p&&L(le),dr(ut),ut===""?G(void 0):be.current=!0,u?.(le)},Pd=(le,ut)=>{le.stopPropagation();let an=ye[ut];da(le,an)},_d=()=>{oe(!1)},Ld=()=>{G(void 0)},Rl=()=>{var le;(le=me.current)==null||le.focus()};ie(()=>{O&&(be.current=!0)},[O]),(0,lr.useEffect)(()=>{Z&&O&&queueMicrotask(()=>{let le=X();le&&be.current&&G(le.data)})},[O,G,Z,X]),(0,lr.useEffect)(()=>{let le;if(!Z){G(void 0);return}ye.length>0&&(le=M(ut=>ut.value===ye[0]).pop()),le||($.current==="ArrowDown"?(le=X(),oe(!0)):$.current==="ArrowUp"&&(le=he(),oe(!0))),le&&G(le?.data)},[Z]);let xs=We(),El=We(),xe=Ee(_o,Tl),Ue=(0,Fn.jsx)(Ct,{"aria-labelledby":V(xs,W),"aria-label":"Show options","aria-expanded":Z,"aria-controls":Z?El:void 0,"aria-haspopup":"listbox",disabled:de,appearance:"transparent",onClick:fa,onFocus:pa,tabIndex:-1,children:Z?(0,Fn.jsx)(j,{"aria-hidden":!0}):(0,Fn.jsx)(_,{"aria-hidden":!0})}),$n=!U&&Dr?(0,Fn.jsxs)(Fn.Fragment,{children:[c,Ue]}):c;return(0,Fn.jsxs)(Gu,{value:fe,children:[(0,Fn.jsx)(kC,{tabIndex:de?void 0:-1,className:V(Qv(),{[Qv("focused")]:pe,[Qv("focusVisible")]:K},a),endAdornment:$n,onChange:Ed,role:U?"textbox":"combobox",disabled:de,readOnly:U,inputProps:{"aria-readonly":U?"true":void 0,"aria-expanded":U?void 0:Z,"aria-controls":Z&&!U?El:void 0,onKeyDown:zr,...I},"aria-activedescendant":re?.id,variant:C,inputRef:ce,value:rn,ref:fr,bordered:N,...Rt({onBlur:Rd,onFocus:on,...P}),pills:p?ye.map(le=>B(le)):[],truncate:D&&!pe&&!Z,onPillRemove:Pd,hidePillClose:!pe||U,emptyReadOnlyMarker:U&&ye.length>0?"":void 0}),(0,Fn.jsx)(qu,{"aria-multiselectable":p,open:(Z||pe)&&!U&&Dr,collapsed:!Z,ref:xe,id:El,tabIndex:-1,...Ft({onMouseOver:_d,onFocus:Rl,onClick:Rl,onMouseLeave:Ld,...R}),left:Cl??0,top:Sl??0,position:kl,width:(r=Oo.floating)==null?void 0:r.offsetWidth,height:(o=Oo.floating)==null?void 0:o.offsetHeight,children:i})]})});var EC=w(F());var PC=w(E());var RC=`.saltText {
  --text-color: currentColor;
}

/* Main css class. Style for body text */
.saltText {
  color: var(--saltText-color, var(--text-color));
  font-family: var(--saltText-fontFamily, var(--salt-text-fontFamily));
  font-size: var(--saltText-fontSize, var(--salt-text-fontSize));
  line-height: var(--saltText-lineHeight, var(--salt-text-lineHeight));
  font-weight: var(--saltText-fontWeight, var(--salt-text-fontWeight));
  letter-spacing: var(--salt-text-letterSpacing);
}

/* Allows truncation */
.saltText-lineClamp {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: var(--text-max-rows, 0);
  overflow: hidden;
  word-break: break-word;
}

/* Primary variant */
.saltText-primary {
  --text-color: var(--salt-content-primary-foreground);
}

/* Disabled primary variant */
.saltText-primary.saltText-disabled {
  --text-color: var(--salt-content-primary-foreground-disabled);
}

/* Secondary variant */
.saltText-secondary {
  --text-color: var(--salt-content-secondary-foreground);
}

/* Disabled secondary variant */
.saltText-secondary.saltText-disabled {
  --text-color: var(--salt-content-secondary-foreground-disabled);
}

/* Info color */
.saltText-info {
  --text-color: var(--salt-status-info-foreground-informative);
}

/* Error color */
.saltText-error {
  --text-color: var(--salt-status-error-foreground-informative);
}

/* Warning color */
.saltText-warning {
  --text-color: var(--salt-status-warning-foreground-informative);
}

/* Success color */
.saltText-success {
  --text-color: var(--salt-status-success-foreground-informative);
}

/* Body emphasis strong */
.saltText strong {
  font-weight: var(--salt-text-fontWeight-strong);
}

/* Body emphasis small */
.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-fontWeight-small);
}

/* Notation */
.saltText-notation.saltText {
  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-notation-fontSize);
  line-height: var(--salt-text-notation-lineHeight);
  font-weight: var(--salt-text-fontWeight);
}

/* Notation emphasis strong */
.saltText-notation.saltText strong {
  font-weight: var(--salt-text-notation-fontWeight-strong);
}

/* Notation emphasis small */
.saltText-notation.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-notation-fontWeight-small);
}

/* Action */
.saltText-action.saltText {
  font-family: var(--salt-text-action-fontFamily);
  letter-spacing: var(--salt-text-action-letterSpacing);
  text-transform: var(--salt-text-action-textTransform);
  text-align: var(--salt-text-action-textAlign);
  font-weight: var(--salt-text-action-fontWeight);
}
.saltText-action.saltText strong {
  font-weight: var(--salt-text-action-fontWeight-strong);
}
.saltText-action.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-action-fontWeight-small);
}

/* Code */
code.saltText,
.saltText-code.saltText {
  font-family: var(--salt-text-code-fontFamily);
}

/* Display 1 */
.saltText-display1.saltText {
  font-family: var(--salt-text-display-fontFamily);
  font-size: var(--salt-text-display1-fontSize);
  font-style: var(--salt-text-display-fontStyle, normal);
  font-weight: var(--salt-text-display-fontWeight);
  letter-spacing: var(--salt-text-display-letterSpacing, var(--salt-text-letterSpacing));
  line-height: var(--salt-text-display1-lineHeight);
  text-transform: var(--salt-text-display-textTransform, none);
}

/* Display 1 emphasis strong */
.saltText-display1.saltText strong {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-strong);
}

/* Display 1 emphasis small */
.saltText-display1.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-small);
}

/* Display 2 */
.saltText-display2.saltText {
  font-family: var(--salt-text-display-fontFamily);
  font-size: var(--salt-text-display2-fontSize);
  font-style: var(--salt-text-display-fontStyle, normal);
  font-weight: var(--salt-text-display-fontWeight);
  letter-spacing: var(--salt-text-display-letterSpacing, var(--salt-text-letterSpacing));
  line-height: var(--salt-text-display2-lineHeight);
  text-transform: var(--salt-text-display-textTransform, none);
}

/* Display 2 emphasis strong */
.saltText-display2.saltText strong {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-strong);
}

/* Display 2 emphasis small */
.saltText-display2.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-small);
}

/* Display 3 */
.saltText-display3.saltText {
  font-family: var(--salt-text-display-fontFamily);
  font-size: var(--salt-text-display3-fontSize);
  font-style: var(--salt-text-display-fontStyle, normal);
  font-weight: var(--salt-text-display-fontWeight);
  letter-spacing: var(--salt-text-display-letterSpacing, var(--salt-text-letterSpacing));
  line-height: var(--salt-text-display3-lineHeight);
  text-transform: var(--salt-text-display-textTransform, none);
}

/* Display 3 emphasis strong */
.saltText-display3.saltText strong {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-strong);
}

/* Display 3 emphasis small */
.saltText-display3.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-small);
}

/* Display 4 */
.saltText-display4.saltText {
  font-family: var(--salt-text-display-fontFamily);
  font-size: var(--salt-text-display4-fontSize);
  font-style: var(--salt-text-display-fontStyle, normal);
  font-weight: var(--salt-text-display-fontWeight);
  letter-spacing: var(--salt-text-display-letterSpacing, var(--salt-text-letterSpacing));
  line-height: var(--salt-text-display4-lineHeight);
  text-transform: var(--salt-text-display-textTransform, none);
}

/* Display 4 emphasis strong */
.saltText-display4.saltText strong {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-strong);
}

/* Display 4 emphasis small */
.saltText-display4.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-display-fontWeight-small);
}

/* Heading 1 */
h1.saltText,
.saltText-h1.saltText {
  font-family: var(--salt-text-heading-fontFamily);
  font-size: var(--salt-text-h1-fontSize);
  font-weight: var(--salt-text-heading-fontWeight);
  line-height: var(--salt-text-h1-lineHeight);
}

/* H1 emphasis strong */
h1.saltText strong,
.saltText-h1.saltText strong {
  font-weight: var(--salt-text-heading-fontWeight-strong);
}

/* H1 emphasis small */
h1.saltText small,
.saltText-h1.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-heading-fontWeight-small);
}

/* Heading 2 */
h2.saltText,
.saltText-h2.saltText {
  font-family: var(--salt-text-heading-fontFamily);
  font-size: var(--salt-text-h2-fontSize);
  font-weight: var(--salt-text-heading-fontWeight);
  line-height: var(--salt-text-h2-lineHeight);
}

/* H2 emphasis strong */
h2.saltText strong,
.saltText-h2.saltText strong {
  font-weight: var(--salt-text-heading-fontWeight-strong);
}

/* H2 emphasis small */
h2.saltText small,
.saltText-h2.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-heading-fontWeight-small);
}

/* Heading 3 */
h3.saltText,
.saltText-h3.saltText {
  font-family: var(--salt-text-heading-fontFamily);
  font-size: var(--salt-text-h3-fontSize);
  font-weight: var(--salt-text-heading-fontWeight);
  line-height: var(--salt-text-h3-lineHeight);
}

/* H3 emphasis strong */
h3.saltText strong,
.saltText-h3.saltText strong {
  font-weight: var(--salt-text-heading-fontWeight-strong);
}

/* H3 emphasis small */
h3.saltText small,
.saltText-h3.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-heading-fontWeight-small);
}

/* Heading 4 */
h4.saltText,
.saltText-h4.saltText {
  font-family: var(--salt-text-heading-fontFamily);
  font-size: var(--salt-text-h4-fontSize);
  font-weight: var(--salt-text-heading-fontWeight);
  line-height: var(--salt-text-h4-lineHeight);
}

/* H4 emphasis strong */
h4.saltText strong,
.saltText-h4.saltText strong {
  font-weight: var(--salt-text-heading-fontWeight-strong);
}

/* H4 emphasis small */
h4.saltText small,
.saltText-h4.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-heading-fontWeight-small);
}

/* Label */
label.saltText,
.saltText-label.saltText {
  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-label-fontSize);
  line-height: var(--salt-text-label-lineHeight);
  font-weight: var(--salt-text-label-fontWeight);
}

/* Label emphasis strong */
label.saltText strong,
.saltText-label.saltText strong {
  font-weight: var(--salt-text-label-fontWeight-strong);
}

/* Label emphasis small */
label.saltText small,
.saltText-label.saltText small {
  font-size: inherit;
  font-weight: var(--salt-text-label-fontWeight-small);
}
`;var Yi=te("saltText"),Ie=(0,PC.forwardRef)(function({as:t,children:n,className:r,disabled:o=!1,maxRows:a,style:l,styleAs:i,variant:s,color:c,...d},p){let g=Y();J({testId:"salt-text",css:RC,window:g});let m=t??"div",b={"--text-max-rows":a,...l},h=s??c??"primary";return(0,EC.jsx)(m,{className:V(Yi(),{[Yi("disabled")]:o,[Yi("lineClamp")]:a,[Yi(i)]:i,[Yi(h)]:h!=="inherit"},r),...d,ref:p,style:b,children:n})});var Qi=w(F()),Xi=w(E());var Zi=(0,Xi.forwardRef)(function({children:t,...n},r){return(0,Qi.jsx)(Ie,{as:"h1",ref:r,...n,children:t})}),Zv=(0,Xi.forwardRef)(function({children:t,...n},r){return(0,Qi.jsx)(Ie,{as:"h2",ref:r,...n,children:t})}),ed=(0,Xi.forwardRef)(function({children:t,...n},r){return(0,Qi.jsx)(Ie,{as:"h3",ref:r,...n,children:t})}),e_=(0,Xi.forwardRef)(function({children:t,...n},r){return(0,Qi.jsx)(Ie,{as:"h4",ref:r,...n,children:t})});var _C=w(F()),LC=w(E());var la=(0,LC.forwardRef)(function({children:t,...n},r){return(0,_C.jsx)(Ie,{as:"label",ref:r,...n,children:t})});var hn=w(F());var Dn=w(E());var OC=`.saltDropdown {
  all: unset;
  box-sizing: border-box;
  min-width: 4em;
  width: 100%;
  background: var(--dropdown-background);
  min-height: var(--salt-size-base);
  border-radius: var(--salt-palette-corner-weak, 0);
  display: inline-flex;
  align-items: center;
  padding: 0 var(--salt-spacing-100);
  color: var(--dropdown-color);
  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-fontWeight);
  line-height: var(--salt-text-lineHeight);
  letter-spacing: var(--salt-text-letterSpacing);
  position: relative;
  overflow: hidden;
}

.saltDropdown:hover {
  cursor: var(--salt-cursor-hover);
}

.saltDropdown-bordered.saltDropdown {
  border: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--dropdown-borderColor);
}

.saltDropdown-bordered.saltDropdown:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--dropdown-borderColor-hover);
}

/* Style applied if focused or active when \`bordered={true}\` */
.saltDropdown-bordered.saltDropdown:focus,
.saltDropdown-bordered.saltDropdown:focus:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--dropdown-borderColor-active);
}

/* Styling when focused if \`disabled={true}\` or \`readOnly={true}\` when \`bordered={true}\` */
.saltDropdown-bordered.saltDropdown[aria-readonly="true"],
.saltDropdown-bordered.saltDropdown[aria-readonly="true"]:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--salt-editable-borderColor-readonly);
}

.saltDropdown-bordered.saltDropdown-disabled,
.saltDropdown-bordered.saltDropdown-disabled:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--salt-editable-borderColor-disabled);
}

.saltDropdown-activationIndicator {
  left: 0;
  bottom: 0;
  width: 100%;
  position: absolute;
  border-bottom: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--dropdown-borderColor);
}

.saltDropdown:hover .saltDropdown-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--dropdown-borderColor-hover);
}

.saltDropdown:focus .saltDropdown-activationIndicator,
.saltDropdown:focus:hover .saltDropdown-activationIndicator {
  border-bottom: var(--salt-size-fixed-200) var(--salt-borderStyle-solid) var(--dropdown-borderColor-active);
}

.saltDropdown[aria-readonly="true"] .saltDropdown-activationIndicator,
.saltDropdown[aria-readonly="true"]:hover .saltDropdown-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--salt-editable-borderColor-readonly);
}

.saltDropdown-disabled .saltDropdown-activationIndicator,
.saltDropdown-disabled:hover .saltDropdown-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--salt-editable-borderColor-disabled);
}

.saltDropdown-bordered .saltDropdown-activationIndicator,
.saltDropdown-bordered.saltDropdown[aria-readonly="true"] .saltDropdown-activationIndicator,
.saltDropdown-bordered.saltDropdown-disabled:hover .saltDropdown-activationIndicator {
  border-bottom-width: 0;
}

.saltDropdown-bordered.saltDropdown:focus .saltDropdown-activationIndicator {
  /* Activation indicator width minus the border from the input. */
  border-bottom-width: var(--salt-size-fixed-100);
}

.saltDropdown-primary {
  --dropdown-color: var(--salt-content-primary-foreground);
  --dropdown-background: var(--salt-editable-primary-background);
  --dropdown-background-disabled: var(--salt-editable-primary-background-disabled);
  --dropdown-background-readonly: var(--salt-editable-background-readonly);
  --dropdown-borderColor: var(--salt-editable-borderColor);
  --dropdown-borderColor-active: var(--salt-editable-borderColor-active);
  --dropdown-borderColor-hover: var(--salt-editable-borderColor-hover);
  --dropdown-outlineColor: var(--salt-focused-outlineColor);
}

.saltDropdown-secondary {
  --dropdown-color: var(--salt-content-primary-foreground);
  --dropdown-background: var(--salt-editable-secondary-background);
  --dropdown-background-disabled: var(--salt-editable-secondary-background-disabled);
  --dropdown-background-readonly: var(--salt-editable-background-readonly);
  --dropdown-borderColor: var(--salt-editable-borderColor);
  --dropdown-borderColor-active: var(--salt-editable-borderColor-active);
  --dropdown-borderColor-hover: var(--salt-editable-borderColor-hover);
  --dropdown-outlineColor: var(--salt-focused-outlineColor);
}

.saltDropdown-tertiary {
  --dropdown-color: var(--salt-content-primary-foreground);
  --dropdown-background: var(--salt-editable-tertiary-background);
  --dropdown-background-disabled: var(--salt-editable-tertiary-background-disabled);
  --dropdown-background-readonly: var(--salt-editable-background-readonly);
  --dropdown-borderColor: var(--salt-editable-borderColor);
  --dropdown-borderColor-active: var(--salt-editable-borderColor-active);
  --dropdown-borderColor-hover: var(--salt-editable-borderColor-hover);
  --dropdown-outlineColor: var(--salt-focused-outlineColor);
}

.saltDropdown-error {
  --dropdown-color: var(--salt-content-primary-foreground);
  --dropdown-background: var(--salt-status-error-background);
  --dropdown-background-readonly: var(--salt-status-error-background);
  --dropdown-borderColor: var(--salt-status-error-borderColor);
  --dropdown-borderColor-active: var(--salt-status-error-borderColor);
  --dropdown-borderColor-hover: var(--salt-status-error-borderColor);
  --dropdown-outlineColor: var(--salt-status-error-borderColor);
}

.saltDropdown-warning {
  --dropdown-color: var(--salt-content-primary-foreground);
  --dropdown-background: var(--salt-status-warning-background);
  --dropdown-background-readonly: var(--salt-status-warning-background);
  --dropdown-borderColor: var(--salt-status-warning-borderColor);
  --dropdown-borderColor-active: var(--salt-status-warning-borderColor);
  --dropdown-borderColor-hover: var(--salt-status-warning-borderColor);
  --dropdown-outlineColor: var(--salt-status-warning-borderColor);
}

.saltDropdown-success {
  --dropdown-color: var(--salt-content-primary-foreground);
  --dropdown-background: var(--salt-status-success-background);
  --dropdown-background-readonly: var(--salt-status-success-background);
  --dropdown-borderColor: var(--salt-status-success-borderColor);
  --dropdown-borderColor-active: var(--salt-status-success-borderColor);
  --dropdown-borderColor-hover: var(--salt-status-success-borderColor);
  --dropdown-outlineColor: var(--salt-status-success-borderColor);
}

.saltDropdown:focus,
.saltDropdown:focus:hover {
  cursor: var(--salt-cursor-hover);
  outline: var(--salt-focused-outlineWidth) var(--salt-focused-outlineStyle) var(--dropdown-outlineColor);
}

.saltDropdown.saltDropdown[aria-readonly="true"] {
  background: var(--dropdown-background-readonly);
  cursor: var(--salt-cursor-readonly);
}

.saltDropdown.saltDropdown:disabled,
.saltDropdown.saltDropdown:disabled:hover {
  background: var(--dropdown-background-disabled);
  cursor: var(--salt-cursor-disabled);
  color: var(--salt-content-primary-foreground-disabled);
}

.saltDropdown-content {
  flex: 1;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  text-wrap: nowrap;
}

.saltDropdown-placeholder {
  color: var(--salt-content-secondary-foreground);
  font-weight: var(--salt-text-fontWeight-small);
}

.saltDropdown-startAdornmentContainer {
  margin-right: var(--salt-spacing-100);
}

.saltDropdown .saltDropdown-toggle {
  margin-left: var(--salt-spacing-100);
}
`;var Mn=te("saltDropdown");function t_({open:e}){let{CollapseIcon:t,ExpandIcon:n}=vn();return e?(0,hn.jsx)(t,{className:Mn("toggle"),"aria-hidden":!0}):(0,hn.jsx)(n,{className:Mn("toggle"),"aria-hidden":!0})}var Jv=(0,Dn.forwardRef)(function(t,n){var r,o;let{className:a,props:l}=_n("saltDropdown",t),{"aria-labelledby":i,"aria-describedby":s,children:c,disabled:d,emptyReadOnlyMarker:p="\u2014",readOnly:g,multiselect:m,onSelectionChange:b,selected:h,defaultSelected:y,defaultOpen:v,value:u,onOpenChange:f,open:x,placeholder:I,startAdornment:C,required:k,variant:T="primary",validationStatus:z,onKeyDown:O,onFocus:A,onBlur:B,valueToString:D=oa,bordered:N=!1,OverlayProps:R,...P}=l,j=Y();J({testId:"salt-dropdown",css:OC,window:j});let{a11yProps:{"aria-describedby":_,"aria-labelledby":W}={},disabled:ee,readOnly:ne,necessity:de,validationStatus:U}=gn(),me=!!d||ee,ce=!!g||ne,be=U??z,fe=de?["required","asterisk"].includes(de):k,re=Ku({open:x,defaultOpen:v,onOpenChange:f,multiselect:m,defaultSelected:y,selected:h,onSelectionChange:b,valueToString:D}),{activeState:G,setActive:Z,openState:se,setOpen:$,openKey:M,getIndexOfOption:X,getOptionsMatching:he,getOptionFromSearch:Se,getFirstOption:ge,getLastOption:ve,getOptionAfter:we,getOptionBefore:ye,getOptionPageAbove:_e,getOptionPageBelow:L,selectedState:K,select:oe,setFocusVisibleState:pe,focusedState:Je,setFocusedState:Hn,listRef:_o,setListRef:rn}=re,dr=K.map(xe=>D(xe)).join(", "),da=u??dr,Lo=ce&&da===""?p:da,Dr=(xe,Ue,$n)=>{ce||$n==="focus"&&xe||$(xe)},{x:Cl,y:Sl,strategy:kl,elements:Oo,floating:Tl,reference:ke,context:$e}=sl({open:se&&!ce&&Dn.Children.count(c)>0,onOpenChange:Dr,placement:"bottom-start",middleware:[uo(1),Zo({apply({rects:xe,elements:Ue,availableHeight:$n}){Ue.floating.style.setProperty("--overlay-minWidth",`${xe.reference.width}px`),Ue.floating.style.setProperty("--overlay-maxHeight",`max(calc((var(--salt-size-base) + var(--salt-spacing-100)) * 5), calc(${$n}px - var(--salt-spacing-100)))`)}}),kr({fallbackStrategy:"initialPlacement"})]}),{getReferenceProps:Rt,getFloatingProps:Ft}=rl([nl($e),bu($e),tl($e)]),fr=(0,Dn.useRef)(null),fa=Ee(ke,fr),pa=Ee(fa,n),zr=(0,Dn.useRef)(""),on=(0,Dn.useRef)(),Rd=xe=>{on.current&&clearTimeout(on.current),zr.current+=xe.key,on.current=window.setTimeout(()=>{zr.current=""},500),se||$(!0,"input");let Ue=Se(zr.current,G);Ue&&(Z(Ue),pe(!0))},Ed=xe=>{var Ue;if(O?.(xe),ce||Vu(xe))return;if(!se){if(xe.key==="ArrowDown"||xe.key==="ArrowUp"||xe.key==="Home"||xe.key==="End"){xe.preventDefault(),$(!0,void 0,xe.key);return}if(fl(xe.key))return}xe.key.length===1&&!xe.ctrlKey&&!xe.metaKey&&!xe.altKey&&(xe.preventDefault(),xe.stopPropagation(),Rd(xe));let $n=G??((Ue=ge())==null?void 0:Ue.data);if($n===void 0)return;let le=fl(xe.key);le&&xe.preventDefault();let ut=le?$I(xe.key,$n,{getFirstOption:ge,getLastOption:ve,getOptionAfter:we,getOptionBefore:ye,getOptionPageAbove:_e,getOptionPageBelow:L}):void 0;switch(xe.key){case"Enter":case" ":if(se&&G?.disabled||zr.current.trim().length>0&&xe.key===" "){xe.preventDefault();return}if(!se||!G)return;xe.preventDefault(),oe(xe,G);break;case"Tab":!m&&G&&oe(xe,G);break}ut&&ut.data.id!==G?.id&&(Z(ut.data),pe(!0))},Pd=xe=>{Hn(!0),A?.(xe)},_d=xe=>{Hn(!1),(!_o.current||!_o.current.contains(xe.relatedTarget))&&B?.(xe)},Ld=()=>{pe(!1)},Rl=()=>{var xe;(xe=fr.current)==null||xe.focus()};(0,Dn.useEffect)(()=>{if(!se){Z(void 0);return}let xe=G?X(G):-1,Ue;xe>=0||(M.current==="Home"?Ue=ge():M.current==="End"&&(Ue=ve()),!Ue&&K.length>0&&(Ue=he($n=>$n.value===K[0]).pop()),Ue||(M.current==="ArrowDown"?Ue=ge():M.current==="ArrowUp"&&(Ue=ve())),Ue||(Ue=ge()),Z(Ue?.data))},[se,c]);let xs=We(),El=Ee(rn,Tl);return(0,hn.jsxs)(Gu,{value:re,children:[(0,hn.jsxs)("button",{className:V(Mn(),Mn(T),{[Mn("disabled")]:me,[Mn(be??"")]:be,[Mn("bordered")]:N},a),ref:pa,role:"combobox",type:"button",disabled:me,"aria-readonly":ce?"true":void 0,"aria-required":fe?"true":void 0,"aria-expanded":se,"aria-activedescendant":G?.id,"aria-labelledby":V(W,i)||void 0,"aria-describedby":V(_,s)||void 0,"aria-controls":se?xs:void 0,...Rt({onKeyDown:Ed,onFocus:Pd,onBlur:_d,...P}),children:[C&&(0,hn.jsx)("div",{className:Mn("startAdornmentContainer"),children:C}),(0,hn.jsx)("span",{className:V(Mn("content"),{[Mn("placeholder")]:!Lo}),children:Lo||I}),!me&&be&&(0,hn.jsx)(gl,{status:be}),!ce&&(0,hn.jsx)(t_,{open:se}),(0,hn.jsx)("div",{className:Mn("activationIndicator")})]}),(0,hn.jsx)(qu,{"aria-multiselectable":m,open:(se||Je)&&!ce&&Dn.Children.count(c)>0,...Ft({onMouseOver:Ld,onFocus:Rl,onClick:Rl,...R}),left:Cl??0,top:Sl??0,position:kl,width:(r=Oo.floating)==null?void 0:r.offsetWidth,height:(o=Oo.floating)==null?void 0:o.offsetHeight,ref:El,id:xs,collapsed:!se,children:c})]})});var AC=w(F());var FC=w(E());var NC=`/* Default variables applied to the root element */
.saltFlexLayout {
  --flexLayout-layout-display: flex;
  --flexLayout-direction: row;
  --flexLayout-wrap: nowrap;
  --flexLayout-justify: flex-start;
  --flexLayout-align: stretch;
  --flexLayout-separator: var(--salt-size-fixed-100);
}

/* Style applied to the root element */
.saltFlexLayout {
  gap: var(--flexLayout-gap);
  margin: var(--flexLayout-margin);
  padding: var(--flexLayout-padding);
  display: var(--flexLayout-layout-display);
  flex-direction: var(--flexLayout-direction);
  flex-wrap: var(--flexLayout-wrap);
  justify-content: var(--flexLayout-justify);
  align-items: var(--flexLayout-align);
  box-sizing: border-box;
}

.saltFlexLayout-separator {
  gap: calc(var(--flexLayout-gap) * 2);
}

.saltFlexLayout-separator > * {
  position: relative;
}
.saltFlexLayout-separator > *:not(:last-child)::after {
  position: absolute;
  display: block;
  content: "";
  background-color: var(--salt-separable-secondary-borderColor);
}

/* Row separator */

.saltFlexLayout-separator-row > *:not(:last-child)::after {
  height: 100%;
}

.saltFlexLayout-separator-row > *:not(:last-child)::after {
  width: var(--flexLayout-separator);
  top: 0;
}
.saltFlexLayout-separator-row-start > *:not(:last-child)::after {
  right: 0;
}
.saltFlexLayout-separator-row-center > *:not(:last-child)::after {
  right: calc(var(--flexLayout-gap) * -1);
}
.saltFlexLayout-separator-row-end > *:not(:last-child)::after {
  right: calc(var(--flexLayout-gap) * -2);
}

/* Column separator */
.saltFlexLayout-separator-column > *:not(:last-child)::after {
  width: 100%;
}

.saltFlexLayout-separator-column > *:not(:last-child)::after {
  height: var(--flexLayout-separator);
  left: 0;
  width: 100%;
}
.saltFlexLayout-separator-column-start > *:not(:last-child)::after {
  bottom: 0;
}
.saltFlexLayout-separator-column-center > *:not(:last-child)::after {
  bottom: calc(var(--flexLayout-gap) * -1);
}
.saltFlexLayout-separator-column-end > *:not(:last-child)::after {
  bottom: calc(var(--flexLayout-gap) * -2);
}
`;var td=te("saltFlexLayout"),MC=["start","end","center"],n_=[...MC,"space-between","space-around","space-evenly"];function BC(e){return e==="start"||e==="end"?`flex-${e}`:e}var wo=(0,FC.forwardRef)(function({as:t,align:n,children:r,className:o,direction:a="row",gap:l=3,margin:i=0,padding:s=0,justify:c,separators:d,style:p,wrap:g=!1,...m},b){let h=Y();J({testId:"salt-flex-layout",css:NC,window:h});let y=t||"div",v=d===!0?"center":d,{matchedBreakpoints:u}=wu(),f=Er(l,u),x=Er(i,u),I=Er(s,u),C=Er(a,u),k=Er(g,u),T={...p,"--flexLayout-align":BC(n),"--flexLayout-direction":C,"--flexLayout-gap":Du(f),"--flexLayout-margin":Du(x),"--flexLayout-padding":Du(I),"--flexLayout-justify":BC(c),"--flexLayout-wrap":k?"wrap":"nowrap"};return(0,AC.jsx)(y,{className:V(td(),{[td("separator")]:v&&!g,[td(`separator-${C??"row"}-${v??"center"}`)]:v&&!g,[td(`separator-${C??"row"}`)]:v&&!g},o),ref:b,style:T,...m,children:r})});var ng=w(F());var ir=w(E());var DC=`.saltFormField {
  display: inline-grid;
  position: relative;
  gap: var(--salt-spacing-100);
  text-align: left;
  width: var(--saltFormField-width, 100%);

  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-fontWeight);
  line-height: var(--salt-text-lineHeight);
  letter-spacing: var(--salt-text-letterSpacing);
}

.saltFormField-labelTop {
  gap: var(--salt-spacing-75);
  grid-auto-rows: min-content;
  grid-template-areas:
    "label"
    "controls";
}

.saltFormField-labelTop.saltFormField-hasControls {
  align-content: start;
  grid-template-rows: min-content minmax(var(--salt-size-base), auto);
}

.saltFormField-labelTop .saltFormFieldHelperText {
  grid-area: 3 / 1;
}

.saltFormField-labelLeft {
  grid-template-columns: var(--saltFormField-label-width, var(--formField-label-width, 40%)) 1fr;
  grid-template-areas: "label controls";
}

.saltFormField-labelLeft.saltFormField-hasControls {
  grid-template-rows: minmax(var(--salt-size-base), auto);
}

.saltFormField-labelRight {
  grid-template-columns: var(--saltFormField-label-width, var(--formField-label-width, 40%)) 1fr;
  grid-template-areas: "label controls";
}

.saltFormField-labelRight.saltFormField-hasControls {
  grid-template-rows: minmax(var(--salt-size-base), auto);
}

.saltFormField-labelLeft .saltFormFieldHelperText,
.saltFormField-labelRight .saltFormFieldHelperText {
  grid-area: 2 / 2;
}

.saltFormField-labelRight .saltFormFieldLabel,
.saltFormField-labelLeft .saltFormFieldLabel {
  padding-top: var(--salt-spacing-100);
}

.saltFormField-labelRight .saltFormFieldLabel {
  text-align: right;
}

.saltFormFieldLabel {
  grid-area: label;
}

.saltFormFieldHelperText {
  grid-area: helperText;
}

.saltFormField-labelTop > :not(.saltFormFieldLabel):not(.saltFormFieldHelperText) {
  align-self: center;
}

.saltFormField-disabled {
  --saltInput-outline: none;
  --saltCheckbox-outline: none;
  --saltRadioButton-outline: none;
}

@supports selector(:has(*)) {
  .saltFormField:not(:has(.saltFormFieldLabel)) {
    grid-template-areas: "controls";
  }

  .saltFormField-hasControls:not(:has(.saltFormFieldLabel)) {
    grid-template-rows: minmax(var(--salt-size-base), auto);
  }
}
`;var Ji=w(F());var Az=w(E());var zC=`.saltFormFieldHelperText {
  cursor: default;
  display: flex;
  flex-direction: row;
  width: 100%;
}

.saltFormFieldHelperText .saltText {
  font-style: var(--saltFormField-helperText-fontStyle, var(--salt-typography-fontStyle-italic, italic));
}

.saltFormFieldHelperText-withValidation {
  column-gap: var(--salt-spacing-75);
}

.saltFormFieldHelperText .saltFormFieldHelperText-statusIndicator {
  margin-top: calc((var(--salt-text-label-lineHeight) - max(var(--salt-size-icon), 12px)) / 2);
}
`;var eg=te("saltFormFieldHelperText"),WC=({className:e,children:t,...n})=>{let r=Y();J({testId:"salt-form-field-helper-text",css:zC,window:r});let{a11yProps:o,disabled:a,readOnly:l,validationStatus:i}=gn();return(0,Ji.jsxs)("div",{className:V(eg(),{[eg("withValidation")]:i},e),children:[!a&&!l&&i&&(0,Ji.jsx)(Bu,{className:eg("statusIndicator"),status:i}),(0,Ji.jsx)(Ie,{disabled:a,id:o?.["aria-describedby"],styleAs:"label",color:i??"secondary",...n,children:t})]})};var nd=w(F());var Kz=w(E());var jC=`.saltFormFieldLabel.saltText {
  font-size: var(--formFieldLabel-fontSize);
  line-height: var(--formFieldLabel-lineHeight);
  font-weight: var(--saltFormField-label-fontWeight, var(--formFieldLabel-fontWeight));
  width: 100%;
}

.saltFormField-labelLeft .saltFormFieldLabel.saltText {
  align-self: baseline;
  padding-top: var(--salt-spacing-100);
}

.saltFormField-labelTop .saltFormFieldLabel.saltText {
  width: fit-content;
}

.saltFormFieldLabel-label {
  --formFieldLabel-fontSize: var(--salt-text-label-fontSize);
  --formFieldLabel-lineHeight: var(--salt-text-label-lineHeight);
  --formFieldLabel-fontWeight: var(--salt-text-label-fontWeight-strong);
  --formFieldLabel-necessity-fontWeight: var(--salt-text-label-fontWeight);
}

.saltFormFieldLabel-sentence {
  --formFieldLabel-fontSize: var(--salt-text-fontSize);
  --formFieldLabel-lineHeight: var(--salt-text-lineHeight);
  --formFieldLabel-fontWeight: var(--salt-text-fontWeight-strong);
  --formFieldLabel-necessity-fontWeight: var(--salt-text-fontWeight);
}

.saltFormFieldLabel-necessityLabel {
  font-style: var(--salt-typography-fontStyle-italic, italic);
  font-weight: var(--formFieldLabel-necessity-fontWeight);
}
`;var tg=te("saltFormFieldLabel"),ia=({className:e,children:t,intent:n="label",onClick:r,...o})=>{let{a11yProps:a,disabled:l,necessity:i,formFieldRef:s}=gn(),c=Y();J({testId:"salt-form-field-label",css:jC,window:c});let d=a?.["aria-labelledby"],p=m=>{if(s?.current){let b=s.current.querySelector(`[aria-labelledby*="${d}"]`);b?.focus(),b?.click()}r?.(m)},g=i?i==="asterisk"?" *":` (${or(i)})`:void 0;return(0,nd.jsxs)(la,{className:V(tg(),tg(n),e),id:d,disabled:l,color:n==="sentence"?"primary":"secondary",onClick:p,...o,children:[t,g&&(0,nd.jsx)("span",{className:tg("necessityLabel"),children:g})]})};var rd=te("saltFormField");function VC(e){return ir.Children.toArray(e).some(t=>(0,ir.isValidElement)(t)?t.type===ir.Fragment?VC(t.props.children):t.type!==ia&&t.type!==WC:!0)}var es=(0,ir.forwardRef)(({children:e,className:t,disabled:n=!1,id:r,labelPlacement:o="top",necessity:a,readOnly:l=!1,validationStatus:i,...s},c)=>{let d=Y();J({testId:"salt-form-field",css:DC,window:d});let p=(0,ir.useRef)(null),g=Ee(c,p),m=We(r),b=VC(e),h=m?`label-${m}`:void 0,y=m?`helperText-${m}`:void 0;return(0,ng.jsx)("div",{ref:g,className:V(rd(),{[rd("disabled")]:n,[rd("hasControls")]:b,[rd(`label${or(o)}`)]:o},t),...s,children:(0,ng.jsx)(ju.Provider,{value:{a11yProps:{"aria-labelledby":h,"aria-describedby":y},disabled:n,necessity:a,readOnly:l,validationStatus:i,formFieldRef:p},children:e})})});var Io=w(F());var od=w(E());var HC=`/* Style applied to the root element */
.saltInput {
  align-items: center;
  background: var(--saltInput-background, var(--input-background));
  border-radius: var(--salt-palette-corner-weak, 0);
  color: var(--saltInput-color, var(--salt-content-primary-foreground));
  display: inline-flex;
  font-family: var(--salt-text-fontFamily);
  font-size: var(--saltInput-fontSize, var(--salt-text-fontSize));
  line-height: var(--saltInput-lineHeight, var(--salt-text-lineHeight));
  letter-spacing: var(--salt-text-letterSpacing);
  height: var(--saltInput-height, var(--salt-size-base));
  min-height: var(--saltInput-minHeight, var(--salt-size-base));
  min-width: var(--saltInput-minWidth, 4em);
  padding-left: var(--saltInput-paddingLeft, var(--salt-spacing-100));
  padding-right: var(--saltInput-paddingRight, var(--salt-spacing-100));
  position: relative;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.saltInput:hover {
  cursor: var(--salt-cursor-text);
}

/* Style applied if \`bordered={true}\` */
.saltInput-bordered.saltInput {
  border: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--input-borderColor);
}

.saltInput-bordered.saltInput:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--input-borderColor-hover);
}

.saltInput-bordered.saltInput-focused,
.saltInput-bordered.saltInput-focused:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--input-borderColor-active);
}

.saltInput-bordered.saltInput-readOnly,
.saltInput-bordered.saltInput-readOnly:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--salt-editable-borderColor-readonly);
}

.saltInput-bordered.saltInput-disabled,
.saltInput-bordered.saltInput-disabled:hover {
  border-style: var(--salt-borderStyle-solid);
  border-color: var(--salt-editable-borderColor-disabled);
}

.saltInput-activationIndicator {
  left: 0;
  bottom: 0;
  width: 100%;
  position: absolute;
  border-bottom: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--input-borderColor);
}

.saltInput:hover .saltInput-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--input-borderColor-hover);
}

.saltInput-focused .saltInput-activationIndicator,
.saltInput-focused:hover .saltInput-activationIndicator {
  border-bottom: var(--salt-size-fixed-200) var(--salt-borderStyle-solid) var(--input-borderColor-active);
}

.saltInput-readOnly .saltInput-activationIndicator,
.saltInput-readOnly:hover .saltInput-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--salt-editable-borderColor-readonly);
}

.saltInput-disabled .saltInput-activationIndicator,
.saltInput-disabled:hover .saltInput-activationIndicator {
  border-bottom-style: var(--salt-borderStyle-solid);
  border-bottom-color: var(--salt-editable-borderColor-disabled);
}

.saltInput-bordered .saltInput-activationIndicator,
.saltInput-bordered.saltInput-readOnly .saltInput-activationIndicator,
.saltInput-bordered.saltInput-disabled:hover .saltInput-activationIndicator {
  border-bottom-width: 0;
}

.saltInput-bordered.saltInput-focused .saltInput-activationIndicator {
  /* Activation indicator width minus the border from the input. */
  border-bottom-width: var(--salt-size-fixed-100);
}

/* Class applied if \`variant="primary"\` */
.saltInput-primary {
  --input-background: var(--salt-editable-primary-background);
  --input-background-disabled: var(--salt-editable-primary-background-disabled);
  --input-background-readonly: var(--salt-editable-background-readonly);
  --input-borderColor: var(--salt-editable-borderColor);
  --input-borderColor-active: var(--salt-editable-borderColor-active);
  --input-borderColor-hover: var(--salt-editable-borderColor-hover);
  --input-outlineColor: var(--salt-focused-outlineColor);
}

/* Class applied if \`variant="secondary"\` */
.saltInput-secondary {
  --input-background: var(--salt-editable-secondary-background);
  --input-background-disabled: var(--salt-editable-secondary-background-disabled);
  --input-background-readonly: var(--salt-editable-background-readonly);
  --input-borderColor: var(--salt-editable-borderColor);
  --input-borderColor-active: var(--salt-editable-borderColor-active);
  --input-borderColor-hover: var(--salt-editable-borderColor-hover);
  --input-outlineColor: var(--salt-focused-outlineColor);
}

/* Class applied if \`variant="tertiary"\` */
.saltInput-tertiary {
  --input-background: var(--salt-editable-tertiary-background);
  --input-background-disabled: var(--salt-editable-tertiary-background-disabled);
  --input-background-readonly: var(--salt-editable-background-readonly);
  --input-borderColor: var(--salt-editable-borderColor);
  --input-borderColor-active: var(--salt-editable-borderColor-active);
  --input-borderColor-hover: var(--salt-editable-borderColor-hover);
  --input-outlineColor: var(--salt-focused-outlineColor);
}

/* Style applied to input if \`validationState="error"\` */
.saltInput-error {
  --input-background: var(--salt-status-error-background);
  --input-background-readonly: var(--salt-status-error-background);
  --input-borderColor: var(--salt-status-error-borderColor);
  --input-borderColor-active: var(--salt-status-error-borderColor);
  --input-borderColor-hover: var(--salt-status-error-borderColor);
  --input-outlineColor: var(--salt-status-error-borderColor);
}

/* Style applied to input if \`validationState="warning"\` */
.saltInput-warning {
  --input-background: var(--salt-status-warning-background);
  --input-background-readonly: var(--salt-status-warning-background);
  --input-borderColor: var(--salt-status-warning-borderColor);
  --input-borderColor-active: var(--salt-status-warning-borderColor);
  --input-borderColor-hover: var(--salt-status-warning-borderColor);
  --input-outlineColor: var(--salt-status-warning-borderColor);
}

/* Style applied to input if \`validationState="success"\` */
.saltInput-success {
  --input-background: var(--salt-status-success-background);
  --input-background-readonly: var(--salt-status-success-background);
  --input-borderColor: var(--salt-status-success-borderColor);
  --input-borderColor-active: var(--salt-status-success-borderColor);
  --input-borderColor-hover: var(--salt-status-success-borderColor);
  --input-outlineColor: var(--salt-status-success-borderColor);
}

/* Styling when focused */
.saltInput-focused,
.saltInput-focused:hover {
  cursor: var(--salt-cursor-text);
  outline: var(--saltInput-outline, var(--salt-focused-outlineWidth) var(--salt-focused-outlineStyle) var(--input-outlineColor));
}

/* Style applied if \`readOnly={true}\` */
.saltInput.saltInput-readOnly {
  background: var(--input-background-readonly);
  cursor: var(--salt-cursor-readonly);
}

/* Style applied to input if \`disabled={true}\` */
.saltInput.saltInput-disabled,
.saltInput.saltInput-disabled:hover {
  background: var(--input-background-disabled);
  cursor: var(--salt-cursor-disabled);
  color: var(--saltInput-color-disabled, var(--salt-content-primary-foreground-disabled));
}

/* Style applied to start adornments */
.saltInput-startAdornmentContainer {
  align-items: center;
  display: inline-flex;
  padding-right: var(--salt-spacing-100);
  column-gap: var(--salt-spacing-100);
}

/* Style applied to end adornments */
.saltInput-endAdornmentContainer {
  align-items: center;
  display: inline-flex;
  padding-left: var(--salt-spacing-100);
  column-gap: var(--salt-spacing-100);
}

.saltInput-readOnly .saltInput-startAdornmentContainer {
  margin-left: var(--salt-spacing-50);
}

.saltInput-startAdornmentContainer .saltButton ~ .saltButton {
  margin-left: calc(-1 * var(--salt-spacing-50));
}

.saltInput-endAdornmentContainer .saltButton ~ .saltButton {
  margin-left: calc(-1 * var(--salt-spacing-50));
}

.saltInput-startAdornmentContainer .saltButton:first-child {
  margin-left: calc(var(--salt-spacing-50) * -1);
}

.saltInput-endAdornmentContainer .saltButton:last-child {
  margin-right: calc(var(--salt-spacing-50) * -1);
}

.saltInput-startAdornmentContainer > .saltButton,
.saltInput-endAdornmentContainer > .saltButton {
  --saltButton-padding: calc(var(--salt-spacing-50) - var(--button-borderWidth));
  --saltButton-height: calc(var(--salt-size-base) - var(--salt-spacing-100));
  --saltButton-borderRadius: var(--salt-palette-corner-weaker);
}

/* Style applied to inner input component */
.saltInput-input {
  background: none;
  border: none;
  box-sizing: content-box;
  color: inherit;
  cursor: inherit;
  display: block;
  flex: 1;
  font: inherit;
  height: 100%;
  letter-spacing: var(--saltInput-letterSpacing, var(--salt-text-letterSpacing));
  margin: 0;
  min-width: 0;
  overflow: hidden;
  padding: 0;
  text-align: var(--input-textAlign, left);
  width: 100%;
}

/* Reset in the  class */
.saltInput-input:focus {
  outline: none;
}

/* Style applied to placeholder text */
.saltInput-input::placeholder {
  color: var(--salt-content-secondary-foreground);
  font-weight: var(--salt-text-fontWeight-small);
}

/* Style applied to selected input if \`disabled={true}\` */
.saltInput-disabled .saltInput-input::selection {
  background: none;
}
`;var zn=te("saltInput");function $C(e){return e==null||e===""||Array.isArray(e)&&e.length===0}var hl=(0,od.forwardRef)(function(t,n){let{className:r,props:o}=_n("saltInput",t),{"aria-activedescendant":a,"aria-expanded":l,"aria-owns":i,disabled:s,emptyReadOnlyMarker:c="\u2014",endAdornment:d,id:p,inputProps:g={},inputRef:m,name:b,placeholder:h,readOnly:y,role:v,startAdornment:u,style:f,textAlign:x="left",value:I,defaultValue:C=I===void 0?"":void 0,validationStatus:k,variant:T="primary",bordered:z=!1,...O}=o,A=Y();J({testId:"salt-input",css:HC,window:A});let{a11yProps:{"aria-describedby":B,"aria-labelledby":D}={},disabled:N,readOnly:R,necessity:P,validationStatus:j}=gn(),_={"aria-activedescendant":a,"aria-expanded":l,"aria-owns":i},W=s||N,ee=y||R,ne=j??k,[de,U]=(0,od.useState)(!1),me=ee&&$C(I),ce=ee&&$C(C),be=I===void 0?void 0:me?c:I,fe=ce?c:C,{"aria-describedby":re,"aria-labelledby":G,onBlur:Z,onChange:se,onFocus:$,required:M,...X}=g,he=P?["required","asterisk"].includes(P):M,[Se,ge]=Ot({controlled:be,default:fe,name:"Input",state:"value"}),ve=L=>{let K=L.target.value;ge(K),se?.(L)},we=L=>{Z?.(L),U(!1)},ye=L=>{$?.(L),U(!0)},_e={"--input-textAlign":x,...f};return(0,Io.jsxs)("div",{className:V(zn(),zn(T),{[zn("focused")]:!W&&de,[zn("disabled")]:W,[zn("readOnly")]:ee,[zn(ne||"")]:ne,[zn("bordered")]:z},r),ref:n,style:_e,...O,children:[u&&(0,Io.jsx)("div",{className:zn("startAdornmentContainer"),children:u}),(0,Io.jsx)("input",{"aria-describedby":V(B,re)||void 0,"aria-labelledby":V(D,G)||void 0,className:V(zn("input"),g?.className),disabled:W,id:p,name:b,readOnly:ee,ref:m,role:v,tabIndex:W?-1:0,onBlur:we,onChange:ve,onFocus:W?void 0:ye,placeholder:h,value:Se,..._,...X,required:he}),!W&&ne&&(0,Io.jsx)(gl,{status:ne}),d&&(0,Io.jsx)("div",{className:zn("endAdornmentContainer"),children:d}),(0,Io.jsx)("div",{className:zn("activationIndicator")})]})});var ad=w(F());var Co=w(E()),KC=w(TI());var UC=`.saltOption {
  color: var(--salt-content-primary-foreground);
  background: var(--salt-selectable-background);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-fontWeight);
  font-family: var(--salt-text-fontFamily);
  line-height: var(--salt-text-lineHeight);
  letter-spacing: var(--salt-text-letterSpacing);
  min-height: calc(var(--salt-size-base) + var(--salt-spacing-100));
  padding: calc(var(--salt-spacing-100) + var(--salt-spacing-25)) var(--salt-spacing-100);
  display: flex;
  gap: var(--salt-spacing-100);
  position: relative;
  cursor: var(--salt-cursor-hover);
  box-sizing: border-box;
  flex-shrink: 0;
}

.saltOption-active {
  background: var(--salt-selectable-background-hover);
}

.saltOption-focusVisible {
  outline: var(--salt-focused-outline);
  outline-offset: calc(var(--salt-size-fixed-100) * -2);
}

.saltOption:hover {
  background: var(--salt-selectable-background-hover);
}

.saltOption[aria-disabled="true"] {
  color: var(--salt-content-primary-foreground);
  background: var(--salt-selectable-background);
  opacity: 0.4;

  cursor: var(--salt-cursor-disabled);
}

.saltOption[aria-selected="true"] {
  z-index: var(--salt-zIndex-default);
  background: var(--salt-selectable-background-selected);
  box-shadow:
    calc(var(--salt-size-fixed-100) * -2) 0 0 0 var(--salt-selectable-background-hover),
    calc(var(--salt-size-fixed-100) * -1) 0 0 var(--salt-size-fixed-100) var(--salt-selectable-borderColor-selected),
    0 calc(var(--salt-size-fixed-100) * -1) 0 var(--salt-selectable-borderColor-selected);
}

/* TODO: Find a better way of doing this */
.saltOption .saltIcon:not(.saltCheckboxIcon-icon) {
  min-height: var(--salt-text-lineHeight);
}
`;var rg=te("saltOption"),l_=(0,Co.forwardRef)(function(t,n){let{className:r,children:o,disabled:a,onClick:l,id:i,value:s,...c}=t,d=Y();J({testId:"salt-option",css:UC,window:d});let p=(0,Co.useRef)(null),g=We(i),{setActive:m,multiselect:b,select:h,register:y,optionStateStore:v,valueToString:u,disabled:f,listRef:x}=tC(),I=a||f,C=String(g),{getSnapshot:k,optionValue:T,subscribe:z}=(0,Co.useMemo)(()=>{let j={id:C,disabled:!!I,value:s};return{getSnapshot:()=>v.getSnapshot(C,j),optionValue:j,subscribe:_=>v.subscribe(C,_)}},[C,I,s,v]),O=(0,KC.useSyncExternalStore)(z,k,k),A=$u(O,2),B=$u(O,1),D=$u(O,4),N=j=>{var _;I||g===void 0||((_=x?.current)==null||_.focus({preventScroll:!0}),m(T),h(j,T),l?.(j))},R=()=>{m(T)};ie(()=>{if(g&&p.current)return y(T,p.current)},[T,g,y]);let P=Ee(p,n);return(0,ad.jsxs)("div",{"aria-disabled":I?"true":void 0,"aria-selected":A,className:V(rg(),{[rg("active")]:B,[rg("focusVisible")]:D},r),ref:P,role:"option",id:g,onClick:N,onMouseOver:R,tabIndex:-1,...c,children:[b&&(0,ad.jsx)(HI,{checked:A}),o??u(s)]})}),ts=(0,Co.memo)(l_);var ld=w(E());function id(e,t=[],n){let r=(0,ld.useRef)(n);return(0,ld.useEffect)(()=>{r.current=e},t),r.current}var qC=w(F());var YC=w(E());var GC=`/* Default variables applied to the root element */
.saltStackLayout {
  --stackLayout-separator-weight: var(--salt-size-fixed-100, 1);
}

.saltStackLayout-separator > * {
  position: relative;
}
.saltStackLayout-separator > *:not(:last-child)::after {
  position: absolute;
  display: block;
  content: "";
  background-color: var(--salt-separable-secondary-borderColor);
}

/*
 * Seperator offset based on seperator alignment
 * var(--stackLayout-separator-weight) is used to take into account the thickness of the seperator,so even at higher weights it will be at the start/center/end
*/
.saltStackLayout-separator-start {
  --stackLayout-seperator-offset: calc(var(--stackLayout-separator-weight) * -1);
}
.saltStackLayout-separator-center {
  --stackLayout-seperator-offset: calc((var(--stackLayout-gap) * -0.5) + (var(--stackLayout-separator-weight) * -0.5));
}
.saltStackLayout-separator-end {
  --stackLayout-seperator-offset: calc(var(--stackLayout-gap) * -1);
}

/* When alignment is 'row' and we have seperators (last child doesn't need a seperator) */
.saltStackLayout-row.saltStackLayout-separator > *:not(:last-child)::after {
  height: 100%;
  width: var(--stackLayout-separator-weight);
  right: var(--stackLayout-seperator-offset);
  top: 0;
}

/* When alignment is 'column' and we have seperators (last child doesn't need a seperator) */
.saltStackLayout-column.saltStackLayout-separator > *:not(:last-child)::after {
  width: 100%;
  height: var(--stackLayout-separator-weight);
  bottom: var(--stackLayout-seperator-offset);
  left: 0;
}
`;var sd=te("saltStackLayout");function i_(e){return e===void 0||typeof e=="string"?e:`calc(var(--salt-spacing-100) * ${e})`}var ns=(0,YC.forwardRef)(function({as:t,children:n,className:r,direction:o="column",gap:a=3,separators:l,style:i,...s},c){let d=Y();J({testId:"salt-stack-layout",css:GC,window:d});let{matchedBreakpoints:p}=wu(),g=Er(a,p),m=l===!0?"center":l,b=Er(o,p),h={...i,"--stackLayout-gap":i_(g)};return(0,qC.jsx)(wo,{as:t,className:V(sd(),{[sd(b??"")]:b,[sd("separator")]:!!m,[m?sd(`separator-${m}`):""]:m},r),ref:c,direction:o,style:h,wrap:!1,gap:g,...s,children:n})});var ZC=w(F());var JC=w(E());var bn=`/* Table: Main css class */
.saltTable {
  --table-header-height: calc(var(--salt-size-base) + var(--salt-spacing-100) + var(--salt-size-fixed-100));
  --table-footer-height: calc(var(--salt-size-base) + var(--salt-spacing-100) + var(--salt-size-fixed-100));
  --table-row-height: calc(var(--salt-size-base) + var(--salt-spacing-100) + var(--salt-size-fixed-100));
}

.saltTable-primary {
  --table-background: var(--salt-container-primary-background);
}

.saltTable-secondary {
  --table-background: var(--salt-container-secondary-background);
}

.saltTable-tertiary {
  --table-background: var(--salt-container-tertiary-background);
}

.saltTable-divider-primary {
  --table-divider-color: var(--salt-separable-primary-borderColor);
}

.saltTable-divider-secondary {
  --table-divider-color: var(--salt-separable-secondary-borderColor);
}

.saltTable-divider-tertiary {
  --table-divider-color: var(--salt-separable-tertiary-borderColor);
}

/* Zebra styling */
table.saltTable-zebra-tertiary tbody tr:nth-of-type(odd) {
  --table-background: var(--salt-container-tertiary-background);
}

table.saltTable-primary.saltTable-zebra tbody tr:nth-of-type(odd) {
  --table-background: var(--salt-container-secondary-background);
}

table.saltTable-secondary.saltTable-zebra tbody tr:nth-of-type(odd) {
  --table-background: var(--salt-container-primary-background);
}

table.saltTable-tertiary.saltTable-zebra tbody tr:nth-of-type(odd) {
  --table-background: var(--salt-container-primary-background);
}

table.saltTable {
  border-spacing: 0;
  border-radius: var(--salt-palette-corner, 0);
  border-collapse: collapse;
  color: var(--salt-content-primary-foreground);
  font-family: var(--salt-text-fontFamily);
  font-size: var(--salt-text-fontSize);
  line-height: var(--salt-text-lineHeight);
  letter-spacing: var(--salt-text-letterSpacing);
  width: 100%;
}

/* TR */
table.saltTable tr {
  background: var(--table-background);
}

table.saltTable tbody tr {
  height: var(--table-row-height);
  min-height: var(--table-row-height);
}

table.saltTable tbody tr:not(:last-child) {
  border-bottom: var(--salt-borderStyle-solid) var(--table-divider-color) var(--salt-size-fixed-100);
}

table.saltTable.saltTable-divider-none tbody tr {
  --table-divider-color: transparent;
}

/* THead */
table.saltTable thead {
  border-start-start-radius: var(--salt-palette-corner);
  border-start-end-radius: var(--salt-palette-corner);
  color: var(--salt-content-secondary-foreground);
  height: var(--table-header-height);
  min-height: var(--table-header-height);
  font-size: var(--salt-text-label-fontSize);
  font-weight: var(--salt-text-label-fontWeight-strong);
  line-height: var(--salt-text-label-lineHeight);
}

table.saltTable thead.saltTable-thead-sticky {
  position: sticky;
  top: 0;
}

table.saltTable thead.saltTable-thead-primary tr {
  background: var(--salt-container-primary-background);
}

table.saltTable thead.saltTable-thead-secondary tr {
  background: var(--salt-container-secondary-background);
}

table.saltTable thead.saltTable-thead-tertiary tr {
  background: var(--salt-container-tertiary-background);
}

table.saltTable thead.saltTable-thead tr {
  border-bottom: var(--salt-borderStyle-solid) var(--table-header-divider-color) var(--salt-size-fixed-100);
}

table.saltTable thead.saltTable-thead-divider-primary {
  --table-header-divider-color: var(--salt-separable-primary-borderColor);
}

table.saltTable thead.saltTable-thead-divider-secondary {
  --table-header-divider-color: var(--salt-separable-secondary-borderColor);
}

table.saltTable thead.saltTable-thead-divider-tertiary {
  --table-header-divider-color: var(--salt-separable-tertiary-borderColor);
}

table.saltTable thead.saltTable-thead-divider-none {
  --table-header-divider-color: transparent;
}

/* TFoot */
table.saltTable tfoot {
  border-end-start-radius: var(--salt-palette-corner);
  border-end-end-radius: var(--salt-palette-corner);
  color: var(--salt-content-primary-foreground);
  height: var(--table-footer-height);
  min-height: var(--table-footer-height);
  font-size: var(--salt-text-fontSize);
  line-height: var(--salt-text-lineHeight);
  font-weight: var(--salt-text-fontWeight-strong);
}

table.saltTable tfoot.saltTable-tfoot-sticky {
  position: sticky;
  bottom: 0;
}

table.saltTable tfoot.saltTable-tfoot tr {
  border-top: var(--salt-borderStyle-solid) var(--table-footer-divider-color) var(--salt-size-fixed-100);
}

table.saltTable tfoot.saltTable-tfoot-primary tr {
  background: var(--salt-container-primary-background);
}

table.saltTable tfoot.saltTable-tfoot-secondary tr {
  background: var(--salt-container-secondary-background);
}

table.saltTable tfoot.saltTable-tfoot-tertiary tr {
  background: var(--salt-container-tertiary-background);
}

table.saltTable tfoot.saltTable-tfoot-divider-primary tr {
  --table-footer-divider-color: var(--salt-separable-primary-borderColor);
}

table.saltTable tfoot.saltTable-tfoot-divider-secondary tr {
  --table-footer-divider-color: var(--salt-separable-secondary-borderColor);
}

table.saltTable tfoot.saltTable-tfoot-divider-tertiary tr {
  --table-footer-divider-color: var(--salt-separable-tertiary-borderColor);
}

table.saltTable tfoot.saltTable-tfoot-divider-none tr {
  --table-footer-divider-color: transparent;
}

/* TH */
table.saltTable th {
  padding: calc(var(--salt-spacing-75) + var(--salt-spacing-50)) var(--salt-spacing-100);
  padding-top: calc(var(--salt-spacing-75) + var(--salt-spacing-50) + var(--salt-size-fixed-100));
  position: relative;
  text-align: start;
  vertical-align: top;
  font-weight: inherit;
}

table.saltTable th.saltTable-th-align-left {
  text-align: start;
}

table.saltTable th.saltTable-th-align-right {
  text-align: end;
}

table.saltTable tbody th[scope="row"] {
  font-weight: var(--salt-text-fontWeight-strong);
  line-height: var(--salt-text-lineHeight);
}

table.saltTable th + th::before {
  background: var(--salt-separable-tertiary-borderColor);
  content: "";
  position: absolute;
  z-index: 1;
  display: block;
  width: var(--salt-size-fixed-100);
  height: calc(100% - var(--salt-spacing-200));
  left: 0;
  top: var(--salt-spacing-100);
}

/* TD */
table.saltTable td {
  height: 100%;
  vertical-align: top;
  padding: calc(var(--salt-spacing-75) + var(--salt-spacing-50)) var(--salt-spacing-100);
}

table.saltTable td.saltTable-td-align-left {
  text-align: start;
}

table.saltTable td.saltTable-td-align-right {
  text-align: end;
}

.saltTable-container {
  width: 100%;
  overflow: auto;
}
`;var QC=w(E());var U4=w(F());var s_=je("TableContext",{id:void 0,setId:()=>{},labelledBy:void 0,setLabelledBy:()=>{}});function XC(){return(0,QC.useContext)(s_)}var nt=te("saltTable"),og=(0,JC.forwardRef)(function(t,n){let r=Y();J({testId:"salt-table",css:bn,window:r});let{children:o,className:a,variant:l="primary",divider:i="tertiary",zebra:s=!1,"aria-labelledby":c,id:d,...p}=t,g=We(d),{setId:m,setLabelledBy:b}=XC(),h=c??g;return ie(()=>{g&&m(g),h&&b(h)},[g,h,m,b]),(0,ZC.jsx)("table",{id:g,className:V(nt(),{[nt(l)]:l,[nt("zebra")]:s,[nt(`divider-${i}`)]:i},a),"aria-labelledby":h,ref:n,...p,children:o})});var e1=w(F());var t1=w(E());var ag=(0,t1.forwardRef)(function({children:t,className:n,...r},o){let a=Y();return J({testId:"salt-table-tbody",css:bn,window:a}),(0,e1.jsx)("tbody",{ref:o,className:V(nt("tbody"),n),...r,children:t})});var n1=w(F());var r1=w(E());var Ar=(0,r1.forwardRef)(function({children:t,className:n,textAlign:r="left",...o},a){let l=Y();return J({testId:"salt-table-td",css:bn,window:l}),(0,n1.jsx)("td",{ref:a,className:Fy(nt("td"),nt("td","align",r),n),...o,children:t})});var o1=w(F());var a1=w(E());var Fr=(0,a1.forwardRef)(function({children:t,className:n,textAlign:r="left",...o},a){let l=Y();return J({testId:"salt-table-th",css:bn,window:l}),(0,o1.jsx)("th",{ref:a,className:V(nt("th"),nt("th","align",r),n),...o,children:t})});var l1=w(F());var i1=w(E());var lg=(0,i1.forwardRef)(function({children:t,className:n,sticky:r=!1,variant:o,divider:a="primary",...l},i){let s=Y();return J({testId:"salt-table-thead",css:bn,window:s}),(0,l1.jsx)("thead",{ref:i,className:V(nt("thead"),{[nt(`thead-${o}`)]:o},{[nt("thead-sticky")]:r},{[nt(`thead-divider-${a}`)]:a},n),...l,children:t})});var s1=w(F());var c1=w(E());var cd=(0,c1.forwardRef)(function({children:t,className:n,...r},o){let a=Y();return J({testId:"salt-table-tr",css:bn,window:a}),(0,s1.jsx)("tr",{ref:o,className:V(nt("tr"),n),...r,children:t})});var So=w(F());var kt=w(E()),g1=w(wi());var u1=w(E());var B3=w(F());var ig=je("TabContext",{focused:!1,selected:!1,disabled:!1,value:"",actions:[],registerAction:()=>()=>{}});function d1(){return(0,u1.useContext)(ig)}var f1=w(E());var D3=w(F());var sg=je("TabsContext",{getFirst:()=>null,getLast:()=>null,getNext:()=>null,getPrevious:()=>null,item:()=>null,getIndex:()=>-1,itemAt:()=>null,sortItems:()=>{},renderMode:"inline",registerBootstrapTab:()=>()=>{},setBootstrapTabReady:()=>{},setBootstrapOverflowReady:()=>{},selected:void 0,registerTab:()=>()=>{},updateTab:()=>{},registerRenderedTab:()=>()=>{},updateRenderedTab:()=>{},getRenderedTab:()=>{},getRenderedTabOrder:()=>-1,renderedTabs:[],registerPanel:()=>()=>{},getPanelId:()=>{},getTabId:()=>{},setSelected:()=>{},activeTab:{current:void 0},selectionFromOverflowValueRef:{current:null},menuOpen:!1,setMenuOpen:()=>{},removalVersion:0,getRemovedItems:()=>new Map});function sr(){return(0,f1.useContext)(sg)}var p1=w(E());function xn(e){return e&&(e.getBoundingClientRect().width||e.clientWidth)||0}function rs(e){if(!e)return 0;let t=e.offsetWidth-e.clientWidth;return Math.max(xn(e),e.scrollWidth+t)}function cg(e){return Number.parseFloat(e.columnGap||e.gap||"0")||0}function ud(e){let t=new Map;for(let n of e)t.set(n,xn(n));return t}function dd(e,t,n,r=.5){let o=e.get(t);return e.set(t,n),o===void 0?!1:Math.abs(o-n)>r}var c_=.5;function u_(e){return e.closest(".saltTabOverflowList-list")||e.closest(".saltTabList-measureContainer")}function m1({hostElement:e,renderMode:t,tabRootRef:n,targetWindow:r,updateRenderedTab:o,value:a}){(0,p1.useEffect)(()=>{if(!e)return;let l=n.current,i=r?.ResizeObserver,s=r?.MutationObserver;if(!l||!i)return;let c=(b=!1)=>{if(!l.isConnected||!b&&u_(l))return;let h=rs(l);h<=c_||o(a,{width:h})},d=null,p=(b=!1)=>{if(!r?.requestAnimationFrame){c(b);return}d!=null&&r.cancelAnimationFrame(d),d=r.requestAnimationFrame(()=>{d=null,c(b)})};t==="portal"?p(!0):c(!0);let g=new i(()=>{c()});g.observe(l);let m=s?new s(()=>{p()}):null;return m?.observe(l,{childList:!0,characterData:!0,subtree:!0}),()=>{d!=null&&r&&r.cancelAnimationFrame(d),m?.disconnect(),g.disconnect()}},[e,t,n,r,o,a])}var v1=`/* Class applied to root Tab element */
.saltTab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  appearance: none;
  -webkit-appearance: none;
  gap: var(--salt-spacing-100);
  border: none;
  border-left: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) transparent;
  border-right: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) transparent;
  white-space: pre;
  min-height: calc(var(--salt-size-base) + var(--salt-spacing-100));
  min-width: 4em;
  padding: var(--salt-spacing-50) var(--salt-spacing-100);
  position: relative;
  flex-shrink: 0;
  box-sizing: border-box;
  overflow: hidden;

  cursor: var(--salt-cursor-hover);
  color: var(--salt-content-primary-foreground);
  font-weight: var(--salt-text-fontWeight);
  font-family: var(--salt-text-fontFamily);
  text-align: var(--salt-text-textAlign);
  letter-spacing: var(--salt-text-letterSpacing);
  line-height: var(--salt-text-lineHeight);
  font-size: var(--salt-text-fontSize);
  max-width: 100%;
}

@supports selector(:has(*)) {
  .saltTabList:has([data-overflowbutton]) .saltTab {
    /* 100% of the tab list but reserving space for the overflow button */
    max-width: calc(100% - var(--salt-spacing-100) - var(--salt-size-base));
  }
}

.saltTab::after {
  content: "";
  position: absolute;
  left: calc(var(--salt-size-fixed-100) * -1);
  right: calc(var(--salt-size-fixed-100) * -1);
  height: var(--salt-size-indicator);
}

.saltTabList-bordered .saltTab::after {
  top: 0;
}

.saltTabList-transparent .saltTab::after {
  bottom: 0;
}

.saltTab:hover::after,
.saltTab-focusVisible::after {
  background: var(--salt-navigable-indicator-hover);
}

.saltTab-disabled:hover::after,
.saltTab-disabled.saltTab-focusVisible::after {
  background: none;
}

.saltTab-focusVisible {
  outline: var(--salt-focused-outline);
}

.saltTabList-bordered .saltTab.saltTab-selected {
  background: var(--saltTabList-activeColor);
  border-left: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--salt-separable-secondary-borderColor);
  border-right: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--salt-separable-secondary-borderColor);
}

.saltTab.saltTab-selected::after {
  background: var(--salt-navigable-accent-indicator-active);
}

.saltTab.saltTab-disabled {
  cursor: var(--salt-cursor-disabled);
  color: var(--salt-content-primary-foreground-disabled);
}
`;var fd=te("saltTab"),os=(0,kt.forwardRef)(function(t,n){let{children:r,className:o,disabled:a,onBlur:l,onMouseDown:i,onFocus:s,onFocusCapture:c,value:d,id:p,...g}=t,m=Y();J({testId:"salt-tab",css:v1,window:m});let{selected:b,activeTab:h,renderMode:y,registerBootstrapTab:v,setBootstrapTabReady:u,registerRenderedTab:f,updateRenderedTab:x}=sr(),I=!!a,C=We(p),k=(0,kt.useRef)(!1),[T,z]=(0,kt.useState)(!1),[O,A]=(0,kt.useState)(!1),[B,D]=(0,kt.useState)(null),N=(0,kt.useRef)(null),R=(0,kt.useRef)(null),P=fe=>{c?.(fe),C&&(h.current={value:d,id:C})},j=fe=>{s?.(fe),A(!0),!k.current&&fe.target.getAttribute("role")==="tab"&&z(!0),k.current=!1},_=fe=>{l?.(fe),A(!1),z(!1)},W=fe=>{i?.(fe),C&&(h.current={value:d,id:C}),k.current=!0},[ee,ne]=(0,kt.useState)(()=>new Set),de=(0,kt.useCallback)(fe=>(ne(re=>{if(re.has(fe))return re;let G=new Set(re);return G.add(fe),G}),()=>{ne(re=>{if(!re.has(fe))return re;let G=new Set(re);return G.delete(fe),G})}),[]),U=(0,kt.useMemo)(()=>Array.from(ee),[ee]),me=(0,kt.useMemo)(()=>({tabId:C,selected:b===d,focused:O,value:d,disabled:I,actions:U,registerAction:de}),[C,b,d,O,I,U,de]);ie(()=>{let fe=m?.document;if(!fe)return;let re=fe.createElement("div");return re.dataset.tabHost=d,re.role="presentation",re.style.display="contents",D(re),()=>{re.remove()}},[m,d]),ie(()=>{if(y==="inline")return v(d)},[v,y,d]),ie(()=>(u(d,B!=null),()=>{u(d,!1)}),[B,u,d]),ie(()=>{if(!(!B||!C))return f({host:B,id:C,marker:N.current,root:R.current,trigger:null,value:d,width:rs(R.current)})},[B,C,f,d]),ie(()=>{let fe={marker:N.current,root:R.current};y==="inline"&&(fe.width=rs(R.current)),x(d,fe)},[y,x,d]),m1({hostElement:B,renderMode:y,tabRootRef:R,targetWindow:m,updateRenderedTab:x,value:d});let ce=Ee(R,n),be=(0,So.jsx)(ig.Provider,{value:me,children:(0,So.jsx)("div",{className:V(fd(),{[fd("selected")]:b===d,[fd("disabled")]:I,[fd("focusVisible")]:T},o),"data-overflowitem":"true","data-value":d,ref:ce,onMouseDown:W,onFocusCapture:P,onFocus:j,onBlur:_,role:"presentation",...g,children:r})});return(0,So.jsxs)(So.Fragment,{children:[(0,So.jsx)("span",{role:"presentation","data-tab-marker":"",hidden:!0,ref:N}),y==="inline"?be:B?(0,g1.createPortal)(be,B):null]})});var ug=w(F());var b1=w(E());var h1=`.saltTabBar {
  display: flex;
  align-items: center;
  flex-direction: row;
  position: relative;
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
}

.saltTabBar-strip {
  display: flex;
  align-items: center;
  flex-direction: row;
  flex: 1 1 auto;
  gap: var(--salt-spacing-100);
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
}

.saltTabBar-divider::before {
  content: "";
  position: absolute;
  inset: auto 0 0 0;
  height: var(--salt-size-fixed-100);
  border-bottom: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--salt-separable-secondary-borderColor);
}

.saltTabBar-inset {
  padding-left: var(--salt-spacing-300);
  padding-right: var(--salt-spacing-300);
}
`;var pd=te("saltTabBar"),dg=(0,b1.forwardRef)(function(t,n){let{className:r,children:o,divider:a,inset:l,...i}=t,s=Y();return J({testId:"salt-tab-bar",css:h1,window:s}),(0,ug.jsx)("div",{className:V(pd(),{[pd("divider")]:a,[pd("inset")]:l},r),...i,ref:n,children:(0,ug.jsx)("div",{className:pd("strip"),children:o})})});var Mr=w(F());var ot=w(E());var x1=w(E());var f5=w(F());var fg=je("TabListLayoutContext",null);function y1(){return(0,x1.useContext)(fg)}var w1=w(E());var g5=w(F());var pg=je("TabSlotRegistryContext",null);function I1(){return(0,w1.useContext)(pg)}var sa=w(E());function C1({maxAttempts:e=120,targetWindow:t}){let n=(0,sa.useRef)(null),r=(0,sa.useCallback)(()=>{n.current!=null&&t&&(t.cancelAnimationFrame(n.current),n.current=null)},[t]),o=(0,sa.useCallback)(a=>{var l;let i=t?.document;if(!i){(l=a())==null||l.focus({preventScroll:!0});return}r();let s=0,c=()=>{let d=a();if(!d?.isConnected){if(s>=e||!t?.requestAnimationFrame)return;s+=1,n.current=t.requestAnimationFrame(c);return}if(d.focus({preventScroll:!0}),i.activeElement===d||s>=e){n.current=null;return}s+=1,t?.requestAnimationFrame?n.current=t.requestAnimationFrame(c):queueMicrotask(c)};c()},[r,e,t]);return(0,sa.useEffect)(()=>()=>{r()},[r]),{cancelScheduledFocus:r,focusElementWithRetry:o}}var mg=w(E());function Wn(e){if(!e||typeof e!="object")return!1;let t=e.ownerDocument,n=t?.defaultView;return!!n&&e instanceof n.HTMLElement}function S1({removalVersion:e,targetWindow:t,tabstripRef:n,overflowListRef:r,handleTabRemoval:o,pendingRemovalRecoveryRef:a,pendingRemovalRecoveryRetriesRef:l}){(0,mg.useEffect)(()=>{if(e<1)return;a.current=!0,l.current=0;let i=t?.requestAnimationFrame(()=>{o()});return()=>{i!=null&&t?.cancelAnimationFrame(i)}},[o,a,l,e,t]),(0,mg.useEffect)(()=>{let i=c=>{var d,p;return c?(((d=n.current)==null?void 0:d.contains(c))??!1)||(((p=r.current)==null?void 0:p.contains(c))??!1):!1},s=c=>{if(!a.current)return;let d=Wn(c.target)&&i(c.target),p=Wn(c.relatedTarget)&&i(c.relatedTarget);d&&!p&&(t?.requestAnimationFrame?t.requestAnimationFrame(()=>o()):queueMicrotask(()=>o()))};return t?.document.addEventListener("focusout",s,!0),()=>{t?.document.removeEventListener("focusout",s,!0)}},[o,r,a,n,t])}var md=w(E());function d_(e){let t=e.activeElement;return!t||t===e.body||t===e.documentElement||!t.isConnected}function f_(e,t){if(!e)return null;let n=e.querySelectorAll(':scope > [data-tabslot] [role="tab"][aria-selected="true"]');return Array.from(n).find(r=>t&&r.id===t?!1:r.isConnected)??null}function k1({activeTab:e,focusElementWithRetry:t,getFirst:n,getIndex:r,getLast:o,getRemovedItems:a,getRenderedTab:l,getSelectedTabElement:i,item:s,itemAt:c,maxRetryAttempts:d,menuOpen:p,overflowButtonRef:g,overflowListRef:m,pendingRemovalRecoveryRef:b,pendingRemovalRecoveryRetriesRef:h,removalRecoveryRafRef:y,selected:v,setSelected:u,tabstripRef:f,targetWindow:x}){let I=(0,md.useCallback)(()=>{b.current=!1,h.current=0},[b,h]),C=Or(()=>{var k;let T=x?.document;if(!T)return;let z=((k=e.current)==null?void 0:k.value)===v,O=()=>{var j,_;if(d_(T))return!0;let W=T.activeElement;return Wn(W)?p?W===g.current?!0:(_=m.current)!=null&&_.contains(W)?W.getAttribute("role")!=="tab":!1:W===g.current?z:((j=f.current)==null?void 0:j.contains(W))&&W.getAttribute("role")!=="tab":!1};if(!O()){if(b.current&&y.current==null)if(h.current<d){if(h.current+=1,!x?.requestAnimationFrame){C();return}y.current=x.requestAnimationFrame(()=>{y.current=null,C()})}else I();return}if(!e.current){I();return}let B=a().get(e.current.id);if(!B){I();return}I();let D=B.value===v,N=B.staleIndex??-1,R=B.id,P=()=>{var j;let _=s(R),W=l(B.value),ee=T.activeElement===g.current;if((j=_?.element)!=null&&j.isConnected&&W?.trigger===_.element&&!(D&&ee)){O()&&t(()=>{var de;return(de=s(R))==null?void 0:de.element});return}if(!O())return;let ne=(N>=0?c(N):null)??(N>0?c(N-1):null)??o()??n();if(ne?.element===g.current){let de=r(ne.id);ne=(de>0?c(de-1):null)??(N>0?c(N-1):null)??n()}ne?.element&&(D&&!p&&!f_(f.current,R)&&(e.current={id:ne.id,value:ne.value},u(null,ne.value)),t(()=>D?i()??ne?.element:ne?.element))};if(!x?.requestAnimationFrame){P();return}x.requestAnimationFrame(()=>{x.requestAnimationFrame(()=>{P()})})});return(0,md.useEffect)(()=>()=>{y.current!=null&&x&&x.cancelAnimationFrame(y.current)},[y,x]),C}var p_=Object.prototype.toString;function T1(e){return typeof e=="function"||p_.call(e)==="[object Function]"}function m_(e){var t=Number(e);return isNaN(t)?0:t===0||!isFinite(t)?t:(t>0?1:-1)*Math.floor(Math.abs(t))}var v_=Math.pow(2,53)-1;function g_(e){var t=m_(e);return Math.min(Math.max(t,0),v_)}function tn(e,t){var n=Array,r=Object(e);if(e==null)throw new TypeError("Array.from requires an array-like object - not null or undefined");if(typeof t<"u"&&!T1(t))throw new TypeError("Array.from: when provided, the second argument must be a function");for(var o=g_(r.length),a=T1(n)?Object(new n(o)):new Array(o),l=0,i;l<o;)i=r[l],t?a[l]=t(i,l):a[l]=i,l+=1;return a.length=o,a}function as(e){"@babel/helpers - typeof";return as=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(t){return typeof t}:function(t){return t&&typeof Symbol=="function"&&t.constructor===Symbol&&t!==Symbol.prototype?"symbol":typeof t},as(e)}function h_(e,t){if(!(e instanceof t))throw new TypeError("Cannot call a class as a function")}function R1(e,t){for(var n=0;n<t.length;n++){var r=t[n];r.enumerable=r.enumerable||!1,r.configurable=!0,"value"in r&&(r.writable=!0),Object.defineProperty(e,E1(r.key),r)}}function b_(e,t,n){return t&&R1(e.prototype,t),n&&R1(e,n),Object.defineProperty(e,"prototype",{writable:!1}),e}function x_(e,t,n){return t=E1(t),t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function E1(e){var t=y_(e,"string");return as(t)=="symbol"?t:t+""}function y_(e,t){if(as(e)!="object"||!e)return e;var n=e[Symbol.toPrimitive];if(n!==void 0){var r=n.call(e,t||"default");if(as(r)!="object")return r;throw new TypeError("@@toPrimitive must return a primitive value.")}return(t==="string"?String:Number)(e)}var w_=(function(){function e(){var t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:[];h_(this,e),x_(this,"items",void 0),this.items=t}return b_(e,[{key:"add",value:function(n){return this.has(n)===!1&&this.items.push(n),this}},{key:"clear",value:function(){this.items=[]}},{key:"delete",value:function(n){var r=this.items.length;return this.items=this.items.filter(function(o){return o!==n}),r!==this.items.length}},{key:"forEach",value:function(n){var r=this;this.items.forEach(function(o){n(o,o,r)})}},{key:"has",value:function(n){return this.items.indexOf(n)!==-1}},{key:"size",get:function(){return this.items.length}}])})(),P1=typeof Set>"u"?Set:w_;function rt(e){var t;return(t=e.localName)!==null&&t!==void 0?t:e.tagName.toLowerCase()}var I_={article:"article",aside:"complementary",button:"button",datalist:"listbox",dd:"definition",details:"group",dialog:"dialog",dt:"term",fieldset:"group",figure:"figure",form:"form",footer:"contentinfo",h1:"heading",h2:"heading",h3:"heading",h4:"heading",h5:"heading",h6:"heading",header:"banner",hr:"separator",html:"document",legend:"legend",li:"listitem",math:"math",main:"main",menu:"list",nav:"navigation",ol:"list",optgroup:"group",option:"option",output:"status",progress:"progressbar",section:"region",summary:"button",table:"table",tbody:"rowgroup",textarea:"textbox",tfoot:"rowgroup",td:"cell",th:"columnheader",thead:"rowgroup",tr:"row",ul:"list"},C_={caption:new Set(["aria-label","aria-labelledby"]),code:new Set(["aria-label","aria-labelledby"]),deletion:new Set(["aria-label","aria-labelledby"]),emphasis:new Set(["aria-label","aria-labelledby"]),generic:new Set(["aria-label","aria-labelledby","aria-roledescription"]),insertion:new Set(["aria-label","aria-labelledby"]),none:new Set(["aria-label","aria-labelledby"]),paragraph:new Set(["aria-label","aria-labelledby"]),presentation:new Set(["aria-label","aria-labelledby"]),strong:new Set(["aria-label","aria-labelledby"]),subscript:new Set(["aria-label","aria-labelledby"]),superscript:new Set(["aria-label","aria-labelledby"])};function S_(e,t){return["aria-atomic","aria-busy","aria-controls","aria-current","aria-description","aria-describedby","aria-details","aria-dropeffect","aria-flowto","aria-grabbed","aria-hidden","aria-keyshortcuts","aria-label","aria-labelledby","aria-live","aria-owns","aria-relevant","aria-roledescription"].some(function(n){var r;return e.hasAttribute(n)&&!((r=C_[t])!==null&&r!==void 0&&r.has(n))})}function _1(e,t){return S_(e,t)}function vd(e){var t=T_(e);if(t===null||ls.indexOf(t)!==-1){var n=k_(e);if(ls.indexOf(t||"")===-1||_1(e,n||""))return n}return t}function k_(e){var t=I_[rt(e)];if(t!==void 0)return t;switch(rt(e)){case"a":case"area":case"link":if(e.hasAttribute("href"))return"link";break;case"img":return e.getAttribute("alt")===""&&!_1(e,"img")?"presentation":"img";case"input":{var n=e,r=n.type;switch(r){case"button":case"image":case"reset":case"submit":return"button";case"checkbox":case"radio":return r;case"range":return"slider";case"email":case"tel":case"text":case"url":return e.hasAttribute("list")?"combobox":"textbox";case"search":return e.hasAttribute("list")?"combobox":"searchbox";case"number":return"spinbutton";default:return null}}case"select":return e.hasAttribute("multiple")||e.size>1?"listbox":"combobox"}return null}function T_(e){var t=e.getAttribute("role");if(t!==null){var n=t.trim().split(" ")[0];if(n.length>0)return n}return null}var ls=["presentation","none"];function Me(e){return e!==null&&e.nodeType===e.ELEMENT_NODE}function vg(e){return Me(e)&&rt(e)==="caption"}function is(e){return Me(e)&&rt(e)==="input"}function L1(e){return Me(e)&&rt(e)==="optgroup"}function O1(e){return Me(e)&&rt(e)==="select"}function N1(e){return Me(e)&&rt(e)==="table"}function B1(e){return Me(e)&&rt(e)==="textarea"}function A1(e){var t=e.ownerDocument===null?e:e.ownerDocument,n=t.defaultView;if(n===null)throw new TypeError("no window available");return n}function F1(e){return Me(e)&&rt(e)==="fieldset"}function M1(e){return Me(e)&&rt(e)==="legend"}function D1(e){return Me(e)&&rt(e)==="slot"}function R_(e){return Me(e)&&e.ownerSVGElement!==void 0}function z1(e){return Me(e)&&rt(e)==="svg"}function W1(e){return R_(e)&&rt(e)==="title"}function ss(e,t){if(Me(e)&&e.hasAttribute(t)){var n=e.getAttribute(t).split(" "),r=e.getRootNode?e.getRootNode():e.ownerDocument;return n.map(function(o){return r.getElementById(o)}).filter(function(o){return o!==null})}return[]}function jn(e,t){return Me(e)?t.indexOf(vd(e))!==-1:!1}function E_(e){return e.trim().replace(/\s\s+/g," ")}function P_(e,t){if(!Me(e))return!1;if(e.hasAttribute("hidden")||e.getAttribute("aria-hidden")==="true")return!0;var n=t(e);return n.getPropertyValue("display")==="none"||n.getPropertyValue("visibility")==="hidden"}function __(e){return jn(e,["button","combobox","listbox","textbox"])||H1(e,"range")}function H1(e,t){if(!Me(e))return!1;switch(t){case"range":return jn(e,["meter","progressbar","scrollbar","slider","spinbutton"]);default:throw new TypeError("No knowledge about abstract role '".concat(t,"'. This is likely a bug :("))}}function j1(e,t){var n=tn(e.querySelectorAll(t));return ss(e,"aria-owns").forEach(function(r){n.push.apply(n,tn(r.querySelectorAll(t)))}),n}function L_(e){return O1(e)?e.selectedOptions||j1(e,"[selected]"):j1(e,'[aria-selected="true"]')}function O_(e){return jn(e,ls)}function N_(e){return vg(e)}function B_(e){return jn(e,["button","cell","checkbox","columnheader","gridcell","heading","label","legend","link","menuitem","menuitemcheckbox","menuitemradio","option","radio","row","rowheader","switch","tab","tooltip","treeitem"])}function A_(e){return!1}function F_(e){return is(e)||B1(e)?e.value:e.textContent||""}function V1(e){var t=e.getPropertyValue("content");return/^["'].*["']$/.test(t)?t.slice(1,-1):""}function $1(e){var t=rt(e);return t==="button"||t==="input"&&e.getAttribute("type")!=="hidden"||t==="meter"||t==="output"||t==="progress"||t==="select"||t==="textarea"}function U1(e){if($1(e))return e;var t=null;return e.childNodes.forEach(function(n){if(t===null&&Me(n)){var r=U1(n);r!==null&&(t=r)}}),t}function M_(e){if(e.control!==void 0)return e.control;var t=e.getAttribute("for");return t!==null?e.ownerDocument.getElementById(t):U1(e)}function D_(e){var t=e.labels;if(t===null)return t;if(t!==void 0)return tn(t);if(!$1(e))return null;var n=e.ownerDocument;return tn(n.querySelectorAll("label")).filter(function(r){return M_(r)===e})}function z_(e){var t=e.assignedNodes();return t.length===0?tn(e.childNodes):t}function gg(e){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},n=new P1,r=typeof Map>"u"?void 0:new Map,o=A1(e),a=t.compute,l=a===void 0?"name":a,i=t.computedStyleSupportsPseudoElements,s=i===void 0?t.getComputedStyle!==void 0:i,c=t.getComputedStyle,d=c===void 0?o.getComputedStyle.bind(o):c,p=t.hidden,g=p===void 0?!1:p,m=function(x,I){if(I!==void 0)throw new Error("use uncachedGetComputedStyle directly for pseudo elements");if(r===void 0)return d(x);var C=r.get(x);if(C)return C;var k=d(x,I);return r.set(x,k),k};function b(f,x){var I="";if(Me(f)&&s){var C=d(f,"::before"),k=V1(C);I="".concat(k," ").concat(I)}var T=D1(f)?z_(f):tn(f.childNodes).concat(ss(f,"aria-owns"));if(T.forEach(function(A){var B=u(A,{isEmbeddedInLabel:x.isEmbeddedInLabel,isReferenced:!1,recursion:!0}),D=Me(A)?m(A).getPropertyValue("display"):"inline",N=D!=="inline"?" ":"";I+="".concat(N).concat(B).concat(N)}),Me(f)&&s){var z=d(f,"::after"),O=V1(z);I="".concat(I," ").concat(O)}return I.trim()}function h(f,x){var I=f.getAttributeNode(x);return I!==null&&!n.has(I)&&I.value.trim()!==""?(n.add(I),I.value):null}function y(f){return Me(f)?h(f,"title"):null}function v(f){if(!Me(f))return null;if(F1(f)){n.add(f);for(var x=tn(f.childNodes),I=0;I<x.length;I+=1){var C=x[I];if(M1(C))return u(C,{isEmbeddedInLabel:!1,isReferenced:!1,recursion:!1})}}else if(N1(f)){n.add(f);for(var k=tn(f.childNodes),T=0;T<k.length;T+=1){var z=k[T];if(vg(z))return u(z,{isEmbeddedInLabel:!1,isReferenced:!1,recursion:!1})}}else if(z1(f)){n.add(f);for(var O=tn(f.childNodes),A=0;A<O.length;A+=1){var B=O[A];if(W1(B))return B.textContent}return null}else if(rt(f)==="img"||rt(f)==="area"){var D=h(f,"alt");if(D!==null)return D}else if(L1(f)){var N=h(f,"label");if(N!==null)return N}if(is(f)&&(f.type==="button"||f.type==="submit"||f.type==="reset")){var R=h(f,"value");if(R!==null)return R;if(f.type==="submit")return"Submit";if(f.type==="reset")return"Reset"}var P=D_(f);if(P!==null&&P.length!==0)return n.add(f),tn(P).map(function(ee){return u(ee,{isEmbeddedInLabel:!0,isReferenced:!1,recursion:!0})}).filter(function(ee){return ee.length>0}).join(" ");if(is(f)&&f.type==="image"){var j=h(f,"alt");if(j!==null)return j;var _=h(f,"title");return _!==null?_:"Submit Query"}if(jn(f,["button"])){var W=b(f,{isEmbeddedInLabel:!1,isReferenced:!1});if(W!=="")return W}return null}function u(f,x){if(n.has(f))return"";if(!g&&P_(f,m)&&!x.isReferenced)return n.add(f),"";var I=Me(f)?f.getAttributeNode("aria-labelledby"):null,C=I!==null&&!n.has(I)?ss(f,"aria-labelledby"):[];if(l==="name"&&!x.isReferenced&&C.length>0)return n.add(I),C.map(function(D){return u(D,{isEmbeddedInLabel:x.isEmbeddedInLabel,isReferenced:!0,recursion:!1})}).join(" ");var k=x.recursion&&__(f)&&l==="name";if(!k){var T=(Me(f)&&f.getAttribute("aria-label")||"").trim();if(T!==""&&l==="name")return n.add(f),T;if(!O_(f)){var z=v(f);if(z!==null)return n.add(f),z}}if(jn(f,["menu"]))return n.add(f),"";if(k||x.isEmbeddedInLabel||x.isReferenced){if(jn(f,["combobox","listbox"])){n.add(f);var O=L_(f);return O.length===0?is(f)?f.value:"":tn(O).map(function(D){return u(D,{isEmbeddedInLabel:x.isEmbeddedInLabel,isReferenced:!1,recursion:!0})}).join(" ")}if(H1(f,"range"))return n.add(f),f.hasAttribute("aria-valuetext")?f.getAttribute("aria-valuetext"):f.hasAttribute("aria-valuenow")?f.getAttribute("aria-valuenow"):f.getAttribute("value")||"";if(jn(f,["textbox"]))return n.add(f),F_(f)}if(B_(f)||Me(f)&&x.isReferenced||N_(f)||A_(f)){var A=b(f,{isEmbeddedInLabel:x.isEmbeddedInLabel,isReferenced:!1});if(A!=="")return n.add(f),A}if(f.nodeType===f.TEXT_NODE)return n.add(f),f.textContent||"";if(x.recursion)return n.add(f),b(f,{isEmbeddedInLabel:x.isEmbeddedInLabel,isReferenced:!1});var B=y(f);return B!==null?(n.add(f),B):(n.add(f),"")}return E_(u(e,{isEmbeddedInLabel:!1,isReferenced:l==="description",recursion:!1}))}function W_(e){return jn(e,["caption","code","deletion","emphasis","generic","insertion","none","paragraph","presentation","strong","subscript","superscript"])}function hg(e){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{};return W_(e)?"":gg(e,t)}var K1=w(E());var t8=w(F());function j_(e){let t=e.activeElement;return!t||t===e.body||t===e.documentElement||!t.isConnected}function V_(e){return hg(e).trim()}function G1({announce:e,focusElementWithRetry:t,getRenderedTab:n,getSelectedTabElement:r,menuOpen:o,resolvedOverflowActiveValue:a,selected:l,selectionFromOverflowValueRef:i,targetWindow:s}){let c=id(l,[l]),d=(0,K1.useCallback)(()=>{t(r)},[t,r]);ie(()=>{!o||!a||t(()=>{var p;return(p=n(a))==null?void 0:p.trigger})},[t,n,o,a]),ie(()=>{let p=s?.document;!p||l===void 0||c===void 0||l===c||j_(p)&&d()},[d,c,l,s]),ie(()=>{let p=i.current;if(p==null||l===void 0||l===c)return;if(l!==p){i.current=null;return}d();let g=r(),m=g&&V_(g)||l;e(`${m} moved to main tab list`,100),i.current=null},[e,r,c,d,l,i])}var cr=w(F());var ko=w(E());var q1=`.saltTabOverflowList {
  position: relative;
}

.saltTabOverflowList-list {
  background: var(--salt-container-primary-background);
  border: var(--salt-size-fixed-100) var(--salt-borderStyle-solid) var(--salt-selectable-borderColor-selected);
  overflow: hidden;
  overflow-y: auto;
  position: absolute;
  box-shadow: var(--salt-overlayable-shadow-popout);
  box-sizing: border-box;
  border-radius: var(--salt-palette-corner, 0);
  z-index: var(--salt-zIndex-flyover);
}

.saltTabOverflowList-listContainer {
  display: flex;
  flex-direction: column;
  gap: var(--salt-spacing-fixed-100);
  max-height: inherit;
  min-height: inherit;
}

.saltTabOverflowList-list .saltTab {
  color: var(--salt-content-primary-foreground);
  background: var(--salt-selectable-background);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-fontWeight);
  min-height: calc(var(--salt-size-base) + var(--salt-spacing-100));
  padding-left: var(--salt-spacing-100);
  padding-right: var(--salt-spacing-100);
  display: flex;
  gap: var(--salt-spacing-100);
  position: relative;
  align-items: center;
  cursor: var(--salt-cursor-hover);
  box-sizing: border-box;
  flex-shrink: 0;
  justify-content: flex-start;
}

@supports selector(:has(*)) {
  .saltTabList:has([data-overflowbutton]) .saltTabOverflowList-list .saltTab {
    max-width: unset;
  }
}

.saltTabOverflowList-list .saltTab .saltTabTrigger {
  justify-content: start;
}

.saltTabOverflowList-list .saltTab::after {
  display: none;
}

.saltTabOverflowList-list .saltTab-focusVisible {
  outline: var(--salt-focused-outline);
  outline-offset: calc(var(--salt-size-fixed-100) * -2);
}

.saltTabOverflowList-list .saltTab:hover {
  background: var(--salt-selectable-background-hover);
}

.saltTabOverflowList-list .saltTab-disabled {
  color: var(--salt-content-primary-foreground-disabled);
  cursor: var(--salt-cursor-disabled);
}

.saltTabOverflowList-list .saltTab-disabled:hover,
.saltTabOverflowList-list .saltTab-disabled:active {
  background: var(--salt-selectable-background);
  box-shadow: none;
}

.saltTabOverflowList-list .saltTab:active {
  background: var(--salt-selectable-background-selected);
  box-shadow:
    0 calc(var(--salt-size-fixed-100) * -1) 0 0 var(--salt-selectable-borderColor-selected),
    0 var(--salt-size-fixed-100) 0 0 var(--salt-selectable-borderColor-selected);
}
`;var Y1=w(F()),Q1=w(E());function cs({slotId:e,value:t,...n}){let r=I1(),o=(0,Q1.useCallback)(a=>{r?.registerSlot(e,a)},[e,r]);return(0,Y1.jsx)("div",{role:"presentation","data-tabslot":"","data-slotid":e,"data-value":t,ref:o,style:{display:"contents"},...n})}var bg=te("saltTabOverflowList"),X1=(0,ko.forwardRef)(function(t,n){var r,o;let{buttonRef:a,className:l,hiddenValues:i,order:s,open:c,setOpen:d,...p}=t,g=Y();J({testId:"salt-tab-overflow-list",css:q1,window:g});let m=(0,ko.useRef)(null),b=(0,ko.useRef)(!1),{OverflowIcon:h}=vn(),{registerTab:y,updateTab:v,activeTab:u}=sr(),{refs:f,x,y:I,strategy:C,context:k,elements:T}=sl({open:c,onOpenChange(de,U,me){var ce;d(de),me==="escape-key"&&((ce=m.current)==null||ce.focus())},placement:"bottom-start",middleware:[uo(1),Zo({apply({elements:de,availableHeight:U}){Object.assign(de.floating.style,{maxHeight:`max(calc((var(--salt-size-base) + var(--salt-spacing-100)) * 5), calc(${U}px - var(--salt-spacing-100)))`})}}),kr(),_i({padding:8})]}),{getFloatingProps:z,getReferenceProps:O}=rl([tl(k),nl(k)]),A=Ee(n,f.setFloating),B=Ee(a,f.setReference),D=Ee(B,m),{Component:N}=Eu(),R=We(),P=We(),j=()=>{R&&(u.current={value:R,id:R})},_=de=>{if(de.key==="Tab"&&de.shiftKey){de.preventDefault(),d(!1);let U=g?.requestAnimationFrame;if(U){U(()=>{var me;return(me=m.current)==null?void 0:me.focus({preventScroll:!0})});return}queueMicrotask(()=>{var me;return(me=m.current)==null?void 0:me.focus({preventScroll:!0})});return}},ee=i.length>0,ne=(0,ko.useRef)(s);return(0,ko.useEffect)(()=>{var de;let U=(de=m.current)==null?void 0:de.parentElement,me=g?.ResizeObserver;if(!c||!U||!me)return;let ce=[U,U.parentElement].filter(re=>re!=null),be=ud(ce),fe=new me(re=>{for(let G of re){if(!Wn(G.target))continue;let Z=G.contentRect.width||xn(G.target);if(dd(be,G.target,Z)){d(!1);return}}});for(let re of ce)fe.observe(re);return()=>{fe.disconnect()}},[c,d,g]),ie(()=>{c&&!ee&&d(!1)},[ee,c,d]),ie(()=>{ee&&!b.current&&d(!1),b.current=ee},[ee,d]),ie(()=>{if(R&&m.current&&ee){let de={id:R,value:R,element:m.current,location:"main",order:ne.current};return y(de)}},[ee,R,y]),ie(()=>{!R||!ee||v(R,{element:m.current,location:"main",order:s})},[ee,s,R,v]),ee?(0,cr.jsxs)(cr.Fragment,{children:[(0,cr.jsx)(Ct,{className:V(bg(),l),"data-overflowbutton":!0,appearance:"transparent",sentiment:"neutral",...O({onFocus:j}),ref:D,"aria-label":"Overflow","aria-expanded":c,"aria-controls":P,role:"tab",tabIndex:-1,...p,children:(0,cr.jsx)(h,{"aria-hidden":!0})}),(0,cr.jsx)(N,{ref:A,...z({id:P,onKeyDown:_}),focusManagerProps:k?{context:k,initialFocus:0,returnFocus:!1,modal:!1,closeOnFocusOut:!0}:void 0,className:bg("list"),open:c,left:x??0,top:I??0,position:C,width:(r=T.floating)==null?void 0:r.offsetWidth,height:(o=T.floating)==null?void 0:o.offsetHeight,children:(0,cr.jsx)("div",{role:"tablist","aria-orientation":"vertical",className:bg("listContainer"),"aria-label":"Overflow tab options",children:i.map(de=>(0,cr.jsx)(cs,{slotId:`overflow:${de}`,value:de},de))})})]}):null});var Qe=w(E());var E8=w(F());function Z1({gap:e,maxWidth:t,overflowWidth:n,pinnedValue:r,tabs:o}){let a=t,l=0,i=0,s=[];for(;i<o.length;){let p=o[i];if(!p)break;if(p.width==null)return null;let g=p.width+e;if(l+g>a)break;l+=g,s.push(p),i+=1}if(i>=o.length)return i;for(a-=n;l>a;){let p=s.pop();if(!p)break;if(p.width==null)return null;l-=p.width+e,i-=1}let d=r==null?null:o.find(p=>p.value===r)??null;if(d&&!s.includes(d)){if(d.width==null)return null;let p=d.width+e;for(;l+p>a;){let g=s.pop();if(!g)break;if(g.width==null)return null;l-=g.width+e,i-=1}}return Math.max(0,i)}function J1(e,t,n){let r=e.slice(0,t),o=e.slice(t),a=n!=null?o.indexOf(n):-1;if(a!==-1){let l=o[a];o=o.filter((i,s)=>s!==a),l!==void 0&&(r=[...r,l])}return{visibleValues:r,hiddenValues:o}}function H_(e){let t=e.width||xn(e.root);return t>.5?t:null}function $_(e){let t=e.parentElement;if(!t)return xn(e);let n=xn(t),r=Br(t).getComputedStyle(t),o=cg(r),a=Array.from(t.children).filter(c=>!Wn(c)||c===e?!1:Br(c).getComputedStyle(c).display!=="none"),l=a.reduce((c,d)=>c+xn(d),0),i=a.length>0?a.length:0;return Math.max(0,n-l-i*o)}function U_(e,t){return e!==void 0&&t.includes(e)}function eS(e,t,n){return t?e:n.current}function nS({container:e,overflowButton:t,tabs:n,selected:r,menuOpen:o}){let a=(0,Qe.useMemo)(()=>n.map(B=>B.value),[n]),l=(0,Qe.useMemo)(()=>n.map(B=>`${B.value}:${B.width.toFixed(2)}`).join("\0"),[n]),[i,s]=(0,Qe.useState)(0),[c,d]=(0,Qe.useState)(!0),[p,g]=(0,Qe.useState)(0),m=(0,Qe.useRef)(r),b=(0,Qe.useRef)(0),h=(0,Qe.useRef)(l),y=(0,Qe.useRef)(o),v=(0,Qe.useRef)(null),u=(0,Qe.useRef)(0),f=a.slice(i),x=U_(r,f),I=eS(r,x,m),C=(0,Qe.useCallback)(()=>eS(r,x,m),[r,x]),k=(0,Qe.useCallback)(()=>{d(!0)},[]),T=(0,Qe.useCallback)(B=>{let D=e.current;if(!D)return null;let N=$_(D),R=Br(D).getComputedStyle(D),P=cg(R),j=t.current?t.current.offsetWidth+P:0,_=n.map(W=>({value:W.value,width:H_(W)}));return Z1({gap:P,maxWidth:N,overflowWidth:j,pinnedValue:B,tabs:_})},[e,t,n]),z=(0,Qe.useCallback)(()=>{let B=e.current,D=v.current;B&&D!=null&&Br(B).cancelAnimationFrame(D),v.current=null,u.current=0},[e]);(0,Qe.useEffect)(()=>z,[z]),ie(()=>{if(r!==void 0&&x){m.current=r;let B=T(r);if(B==null){k();return}B!==i&&s(B),c&&d(!1)}},[c,k,T,r,x,i]),(0,Qe.useEffect)(()=>{let B=e.current;if(!B||o||c)return;let D=[B],N=B.parentElement;if(N){D.push(N);for(let _ of Array.from(N.children))Wn(_)&&_!==B&&D.push(_)}let R=ud(D),P=Br(B).ResizeObserver;if(!P)return;let j=new P(_=>{for(let W of _){if(!Wn(W.target))continue;let ee=W.contentRect.width;if(dd(R,W.target,ee)){let ne=T(C());if(ne!=null&&ne===i)continue;k();return}}});for(let _ of D)j.observe(_);return()=>{j.disconnect()}},[e,C,c,k,T,o,i]),ie(()=>{y.current&&!o&&k(),y.current=o},[k,o]),ie(()=>{var B;let D=((B=t.current)==null?void 0:B.offsetWidth)??0;b.current!==D&&(b.current=D,i<n.length&&k())}),ie(()=>{h.current!==l&&(h.current=l,k())},[k,l]),ie(()=>{if(!c||o)return;let B=T(C());if(B==null){if(v.current!=null)return;let D=e.current;if(!D||xn(D)<=.5){u.current=0;return}if(u.current>=5)return;u.current+=1,v.current=Br(D).requestAnimationFrame(()=>{v.current=null,g(N=>N+1)});return}z(),s(B),d(!1)},[z,e.current,C,c,p,T,o]);let{visibleValues:O,hiddenValues:A}=J1(a,i,I);return[O,A,c]}var yn=w(E());function K_(e,t,n){let r=e.indexOf(t),o=n!=null?e.indexOf(n):0;return r>=0?r:Math.max(0,o)}function rS({hiddenValues:e,menuOpen:t,overflowMenuOpen:n,visibleValues:r}){let[o,a]=(0,yn.useState)(null);(0,yn.useEffect)(()=>{n||a(null)},[n]);let l=(0,yn.useMemo)(()=>n?o&&e.includes(o)?o:e[0]??null:null,[e,n,o]),i=(0,yn.useMemo)(()=>new Set(e),[e]),s=(0,yn.useMemo)(()=>new Set(r),[r]),c=(0,yn.useCallback)(g=>s.has(g)?"main":t&&i.has(g)?"overflow":"hidden",[i,t,s]),d=(0,yn.useCallback)((g,m)=>{if(e.length<1)return!1;let b=K_(e,m,l),h=e.length-1,y=b;switch(g){case"ArrowDown":y=b>=h?0:b+1;break;case"ArrowUp":y=b<=0?h:b-1;break;case"Home":y=0;break;case"End":y=h;break}let v=e[y];return v?(a(v),!0):!1},[e,l]),p=(0,yn.useMemo)(()=>({getLocation:c,overflowActiveValue:l,setOverflowActiveValue:a,moveOverflowFocus:d}),[c,d,l]);return{resolvedOverflowActiveValue:l,tabListLayoutContext:p}}var oS=`/* Component class applied to the root element */
.saltTabList {
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-start;
  align-items: center;
  position: relative;
  background: transparent;
  min-height: calc(var(--salt-size-base) + var(--salt-spacing-100));
  gap: var(--salt-spacing-100);
  max-width: 100%;
  min-width: 0;
  flex: 0 1 auto;
}

.saltTabList-center {
  justify-content: center;
}

.saltTabList-right {
  justify-content: flex-end;
}

.saltTabList-activeColorPrimary {
  --saltTabList-activeColor: var(--salt-container-primary-background);
}

.saltTabList-activeColorSecondary {
  --saltTabList-activeColor: var(--salt-container-secondary-background);
}

.saltTabList-activeColorTertiary {
  --saltTabList-activeColor: var(--salt-container-tertiary-background);
}

.saltTabList-measureContainer {
  position: absolute;
  top: 0;
  left: 0;
  height: 0;
  overflow: hidden;
  pointer-events: none;
  visibility: hidden;
  white-space: nowrap;
}
`;var us=te("saltTabList"),aS=120,xg=(0,ot.forwardRef)(function(t,n){let{appearance:r="bordered",activeColor:o="primary",children:a,className:l,onKeyDown:i,...s}=t,c=Y();J({testId:"salt-tab-list",css:oS,window:c});let{renderMode:d,selected:p,setSelected:g,setBootstrapOverflowReady:m,getNext:b,getPrevious:h,getFirst:y,getLast:v,getIndex:u,item:f,itemAt:x,activeTab:I,selectionFromOverflowValueRef:C,menuOpen:k,setMenuOpen:T,sortItems:z,getRemovedItems:O,getRenderedTab:A,renderedTabs:B,removalVersion:D}=sr(),N=(0,ot.useRef)(null),R=(0,ot.useRef)(null),P=(0,ot.useRef)(new Map),j=(0,ot.useRef)(null),_=(0,ot.useRef)(!1),W=(0,ot.useRef)(0),[ee,ne]=(0,ot.useState)(0),de=Ee(N,n),U=(0,ot.useRef)(null),{announce:me}=Au(),ce=d==="portal"?k:!1,[be,fe,re]=nS({container:N,menuOpen:ce,selected:p,tabs:B,overflowButton:U});(0,ot.useEffect)(()=>{m(d==="inline"&&B.length>0&&!re)},[re,d,B.length,m]);let{resolvedOverflowActiveValue:G,tabListLayoutContext:Z}=rS({hiddenValues:fe,menuOpen:k,overflowMenuOpen:ce,visibleValues:be}),se=(0,ot.useCallback)((ve,we)=>{(P.current.get(ve)??null)!==we&&(we?P.current.set(ve,we):P.current.delete(ve),ne(_e=>_e+1))},[]),$=(0,ot.useMemo)(()=>({registerSlot:se}),[se]),M=(0,ot.useMemo)(()=>{let ve=new Map;for(let we of be)ve.set(we,`main:${we}`);for(let we of fe)ve.set(we,k?`overflow:${we}`:`measure:${we}`);return{map:ve,version:ee}},[fe,k,ee,be]);ie(()=>{var ve;if(d==="portal")for(let[we,ye]of M.map){let _e=(ve=A(we))==null?void 0:ve.host,L=P.current.get(ye);_e&&L&&_e.parentElement!==L&&L.appendChild(_e)}},[A,d,M]);let X=ve=>{var we,ye;if(i?.(ve),k)return;let L={ArrowRight:b,ArrowLeft:h,Home:y,End:v}[ve.key];if(L){ve.preventDefault(),z();let K=(we=I.current)==null?void 0:we.id;if(!K)return;let oe=L(K);oe&&((ye=oe.element)==null||ye.focus({preventScroll:!0}))}},he=(0,ot.useCallback)(()=>{var ve,we,ye;return((ve=N.current)==null?void 0:ve.querySelector('[role="tab"][aria-selected="true"]'))??((ye=f((we=I.current)==null?void 0:we.id))==null?void 0:ye.element)},[f,I]),{focusElementWithRetry:Se}=C1({maxAttempts:aS,targetWindow:c});G1({announce:me,focusElementWithRetry:Se,getRenderedTab:A,getSelectedTabElement:he,menuOpen:k,resolvedOverflowActiveValue:G,selected:p,selectionFromOverflowValueRef:C,targetWindow:c});let ge=k1({activeTab:I,focusElementWithRetry:Se,getFirst:y,getIndex:u,getLast:v,getRemovedItems:O,getRenderedTab:A,getSelectedTabElement:he,item:f,itemAt:x,maxRetryAttempts:aS,menuOpen:k,overflowButtonRef:U,overflowListRef:R,pendingRemovalRecoveryRef:_,pendingRemovalRecoveryRetriesRef:W,removalRecoveryRafRef:j,selected:p,setSelected:g,tabstripRef:N,targetWindow:c});return S1({removalVersion:D,targetWindow:c,tabstripRef:N,overflowListRef:R,handleTabRemoval:ge,pendingRemovalRecoveryRef:_,pendingRemovalRecoveryRetriesRef:W}),(0,Mr.jsx)("div",{role:"tablist",className:V(us(),us(r),us("horizontal"),us(`activeColor${or(o)}`),l),"data-ismeasuring":d==="portal"&&re?!0:void 0,ref:de,onKeyDown:X,...s,children:d==="inline"?a:(0,Mr.jsx)(pg.Provider,{value:$,children:(0,Mr.jsxs)(fg.Provider,{value:Z,children:[a,be.map(ve=>(0,Mr.jsx)(cs,{slotId:`main:${ve}`,value:ve},ve)),!k&&fe.length>0?(0,Mr.jsx)("div",{"aria-hidden":"true",role:"presentation",className:us("measureContainer"),children:fe.map(ve=>(0,Mr.jsx)(cs,{slotId:`measure:${ve}`,value:ve},`measure-${ve}`))}):null,(0,Mr.jsx)(X1,{buttonRef:U,hiddenValues:fe,open:k,order:B.length,setOpen:T,ref:R})]})})})});var iS=w(F());var To=w(E());var lS=`.saltTabPanel {
  height: 100%;
  width: 100%;
}

.saltTabPanel[hidden] {
  display: none;
}

.saltTabPanel:focus-visible {
  outline: var(--salt-focused-outline);
}
`;var G_=te("saltTabPanel"),ds=(0,To.forwardRef)(function(t,n){let{className:r,children:o,id:a,value:l,...i}=t,s=Y();J({testId:"salt-tab-panel",css:lS,window:s});let c=We(a),{registerPanel:d,getTabId:p,selected:g}=sr(),m=g!==l,b=(0,To.useRef)(null),h=Ee(b,n);ie(()=>{if(c)return d(c,l)},[l,c,d]);let[y,v]=(0,To.useState)(!1);(0,To.useEffect)(()=>{let f=b.current,x=s?.MutationObserver;if(!f||m)return;let I=null,C=()=>{I=null;let O=co(f).length>0;v(A=>A===O?A:O)},k=()=>{if(I!=null&&s&&s.cancelAnimationFrame(I),!s?.requestAnimationFrame){C();return}I=s.requestAnimationFrame(C)},T=x?new x(()=>{k()}):null;return k(),T?.observe(f,{childList:!0,subtree:!0,attributes:!0}),()=>{T?.disconnect(),I!=null&&s&&s.cancelAnimationFrame(I)}},[m,s]);let u=p(l);return(0,iS.jsx)("div",{id:c,ref:h,role:"tabpanel","aria-labelledby":u,className:V(G_(),r),hidden:m||void 0,tabIndex:m||y?void 0:0,...i,children:o})});var yg=w(F());var Tt=w(E());var ca=w(E());var g6=w(F());function sS({commitSelection:e,menuOpen:t,selected:n,setMenuOpen:r}){let o=id(n,[n]),a=(0,ca.useRef)(null),l=(0,ca.useRef)(null),i=(0,ca.useCallback)((s,c,d="main")=>{let p=d==="overflow";if(a.current=p?c:null,p){s?.persist(),l.current={event:s,value:c},r(!1);return}l.current=null,r(!1),e(s,c)},[e,r]);return ie(()=>{if(t)return;let s=l.current;s&&(l.current=null,e(s.event,s.value))},[e,t]),(0,ca.useEffect)(()=>{if(t)return;let s=a.current;if(s==null||l.current||n===s&&n!==o)return;let c=setTimeout(()=>{a.current===s&&(a.current=null)});return()=>clearTimeout(c)},[t,o,n]),{selectionFromOverflowValueRef:a,setSelected:i}}var Ve=w(E());function q_(e){let t=e.map((r,o)=>[o,r]),n=!1;return t.sort(([r,o],[a,l])=>{if(o.order!=null&&o.order>=0&&l.order!=null&&l.order>=0&&o.order!==l.order)return(o.order<l.order&&r>a||o.order>l.order&&r<a)&&(n=!0),o.order-l.order;let i=o.element,s=l.element;if(i===s||!i||!s)return 0;let c=i.compareDocumentPosition(s);return c&Node.DOCUMENT_POSITION_DISCONNECTED?0:c&Node.DOCUMENT_POSITION_FOLLOWING?(r>a&&(n=!0),-1):(r<a&&(n=!0),1)}),n?t.map(([r,o])=>o):e}function cS({wrap:e,targetWindow:t}){let n=(0,Ve.useRef)([]),r=(0,Ve.useRef)(new Map),o=(0,Ve.useRef)(new Map),[a,l]=(0,Ve.useState)(0),i=(0,Ve.useCallback)(()=>q_(Array.from(r.current.values())),[]),s=(0,Ve.useCallback)(()=>i().filter(h=>h.location==="hidden"?!1:!!h.element),[i]),c=(0,Ve.useCallback)(()=>{n.current=i()},[i]),d=(0,Ve.useCallback)(()=>{let h=new Map(o.current);return o.current.clear(),h},[]),p=(0,Ve.useRef)(null),g=(0,Ve.useCallback)(()=>{if(!t?.requestAnimationFrame){c();return}p.current!=null&&t.cancelAnimationFrame(p.current),p.current=t.requestAnimationFrame(()=>{p.current=null,c()})},[c,t]),m=(0,Ve.useCallback)(h=>(r.current.set(h.id,h),o.current.delete(h.id),g(),()=>{let y=i(),v=r.current.get(h.id)??h,u=y.findIndex(({id:f})=>f===h.id);o.current.set(h.id,{...v,staleIndex:u}),n.current=y.filter(({id:f})=>f!==h.id),r.current.delete(h.id),l(f=>f+1)}),[i,g]),b=(0,Ve.useCallback)((h,y)=>{let v=r.current.get(h);if(!v)return;let u=!1,f={...v};for(let[x,I]of Object.entries(y)){let C=x;f[C]!==I&&(u=!0,f[C]=I)}u&&(r.current.set(h,f),n.current=n.current.map(x=>x.id!==h?x:f),g())},[g]);return(0,Ve.useEffect)(()=>()=>{p.current!=null&&t&&t.cancelAnimationFrame(p.current)},[t]),{registerItem:m,item:(0,Ve.useCallback)(h=>{if(!h)return null;let y=r.current.get(h);return y||(y=n.current.find(v=>v.id===h),y&&r.current.set(y.id,y)),y??null},[]),getNext:(0,Ve.useCallback)(h=>{let y=s();if(y.length===0)return null;let v=y.findIndex(({id:f})=>f===h);if(v===-1)return y[0];let u=(v+1)%y.length;return y[u]??null},[s,e]),getPrevious:(0,Ve.useCallback)(h=>{let y=s();if(y.length===0)return null;let v=y.findIndex(({id:f})=>f===h);if(v===-1)return y[y.length-1];let u=(v-1+y.length)%y.length;return y[u]??null},[s,e]),getFirst:(0,Ve.useCallback)(()=>s()[0]??null,[s]),getLast:(0,Ve.useCallback)(()=>{let h=s();return h[h.length-1]??null},[s]),getIndex:(0,Ve.useCallback)(h=>s().findIndex(({id:y})=>y===h),[s]),itemAt:(0,Ve.useCallback)(h=>s()[h]??null,[s]),updateItem:b,getRemovedItems:d,removalVersion:a,sortItems:c}}var gt=w(E());var I6=w(F());function Y_(e){return[...e].sort((t,n)=>{if(t.marker===n.marker||!t.marker||!n.marker)return 0;let r=t.marker.compareDocumentPosition(n.marker);return r&Node.DOCUMENT_POSITION_FOLLOWING?-1:r&Node.DOCUMENT_POSITION_PRECEDING?1:0})}function uS(){let[e,t]=(0,gt.useState)(()=>new Map),[n,r]=(0,gt.useState)("inline"),[o,a]=(0,gt.useState)(()=>new Set),[l,i]=(0,gt.useState)(()=>new Set),[s,c]=(0,gt.useState)(!1),d=(0,gt.useCallback)(f=>(a(x=>{if(x.has(f))return x;let I=new Set(x);return I.add(f),I}),()=>{a(x=>{if(!x.has(f))return x;let I=new Set(x);return I.delete(f),I}),i(x=>{if(!x.has(f))return x;let I=new Set(x);return I.delete(f),I})}),[]),p=(0,gt.useCallback)((f,x)=>{i(I=>{let C=I.has(f);if(x===C)return I;let k=new Set(I);return x?k.add(f):k.delete(f),k})},[]),g=(0,gt.useCallback)(f=>{c(x=>x===f?x:f)},[]);ie(()=>{if(!(n==="portal"||o.size<1)&&s){for(let f of o){if(!l.has(f))return;let x=e.get(f);if(!x||xn(x.root)<=0)return}r("portal")}},[s,o,l,n,e]);let m=(0,gt.useCallback)(f=>(t(x=>{if(x.get(f.value)===f)return x;let C=new Map(x);return C.set(f.value,f),C}),()=>{t(x=>{let I=x.get(f.value);if(!I||I.id!==f.id)return x;let C=new Map(x);return C.delete(f.value),C})}),[]),b=(0,gt.useCallback)((f,x)=>{t(I=>{let C=I.get(f);if(!C)return I;let k=!1,T={...C};for(let[O,A]of Object.entries(x)){let B=O;T[B]!==A&&(k=!0,T[B]=A)}if(!k)return I;let z=new Map(I);return z.set(f,T),z})},[]),h=(0,gt.useCallback)(f=>e.get(f),[e]),y=(0,gt.useMemo)(()=>Y_(Array.from(e.values())),[e]),v=(0,gt.useMemo)(()=>new Map(y.map((f,x)=>[f.value,x])),[y]),u=(0,gt.useCallback)(f=>v.get(f)??-1,[v]);return{renderMode:n,registerBootstrapTab:d,setBootstrapTabReady:p,setBootstrapOverflowReady:g,registerRenderedTab:m,updateRenderedTab:b,getRenderedTab:h,getRenderedTabOrder:u,renderedTabs:y}}var dS=`.saltTabs {
  min-width: 0;
}
`;var Q_=te("saltTabs");function fS(e,t,n){if(e.get(t)===n)return e;let r=new Map(e);return r.set(t,n),r}function pS(e,t,n){if(e.get(t)!==n)return e;let r=new Map(e);return r.delete(t),r}var wg=(0,Tt.forwardRef)(function(t,n){let{className:r,children:o,value:a,defaultValue:l,onChange:i,...s}=t,c=Y();J({testId:"salt-tabs",css:dS,window:c});let[d,p]=(0,Tt.useState)(()=>new Map),[g,m]=(0,Tt.useState)(()=>new Map),{renderMode:b,registerBootstrapTab:h,setBootstrapTabReady:y,setBootstrapOverflowReady:v,registerRenderedTab:u,updateRenderedTab:f,getRenderedTab:x,getRenderedTabOrder:I,renderedTabs:C}=uS(),{registerItem:k,updateItem:T,item:z,getNext:O,getPrevious:A,getFirst:B,getLast:D,itemAt:N,getIndex:R,sortItems:P,removalVersion:j,getRemovedItems:_}=cS({targetWindow:c,wrap:!0}),W=(0,Tt.useRef)(),[ee,ne]=(0,Tt.useState)(!1),[de,U]=Ot({controlled:a,default:l,name:"Tabs",state:"selected"}),me=(0,Tt.useCallback)(($,M)=>{U(M),de!==M&&i?.($,M)},[i,de]),{selectionFromOverflowValueRef:ce,setSelected:be}=sS({commitSelection:me,menuOpen:ee,selected:de,setMenuOpen:ne}),fe=(0,Tt.useCallback)($=>{let M=k($);return p(X=>fS(X,$.value,$.id)),()=>{M(),p(X=>pS(X,$.value,$.id))}},[k]),re=(0,Tt.useCallback)(($,M)=>(m(X=>fS(X,M,$)),()=>{m(X=>pS(X,M,$))}),[]),G=(0,Tt.useCallback)($=>g.get($),[g]),Z=(0,Tt.useCallback)($=>d.get($),[d]),se=(0,Tt.useMemo)(()=>({renderMode:b,registerBootstrapTab:h,setBootstrapTabReady:y,setBootstrapOverflowReady:v,registerTab:fe,updateTab:T,registerRenderedTab:u,updateRenderedTab:f,getRenderedTab:x,getRenderedTabOrder:I,renderedTabs:C,registerPanel:re,getPanelId:G,getTabId:Z,selected:de,setSelected:be,item:z,getNext:O,getPrevious:A,getFirst:B,getLast:D,activeTab:W,selectionFromOverflowValueRef:ce,menuOpen:ee,setMenuOpen:ne,itemAt:N,getIndex:R,sortItems:P,removalVersion:j,getRemovedItems:_}),[b,h,y,v,re,fe,T,u,f,x,I,C,G,Z,de,be,z,O,A,B,D,ee,N,R,P,j,_,ce]);return(0,yg.jsx)(sg.Provider,{value:se,children:(0,yg.jsx)("div",{className:V(Q_(),r),ref:n,...s,children:o})})});var vS=w(F());var bl=w(E());var mS=`.saltTabTrigger {
  all: unset;
  display: flex;
  gap: var(--salt-spacing-100);
  align-items: center;
  justify-content: center;
  flex: 1;
  overflow: hidden;
}

/* The action should be triggered by clicking anywhere on the tab. */
.saltTabTrigger::before {
  content: "";
  position: absolute;
  width: 100%;
  height: 100%;
  left: 0;
  top: 0;
}

.saltTabTrigger:focus-visible {
  outline: none;
}
`;var X_=te("saltTabTrigger");function Z_(e){if(!(e<1))return e===1?"1 action available":`${e} actions available`}var J_=typeof HTMLElement<"u"&&"ariaActions"in HTMLElement.prototype,fs=(0,bl.forwardRef)(function(t,n){let{children:r,className:o,onClick:a,onKeyDown:l,onFocus:i,...s}=t,c=Y();J({testId:"salt-tab-trigger",css:mS,window:c});let{setSelected:d,registerTab:p,updateTab:g,updateRenderedTab:m,getRenderedTabOrder:b,getPanelId:h,getTabId:y,selected:v,activeTab:u,menuOpen:f,setMenuOpen:x}=sr(),{selected:I,value:C,focused:k,disabled:T,tabId:z,actions:O}=d1(),A=y1(),B=(0,bl.useRef)(null),D=A?.getLocation(C)??"main",N=D==="overflow"?"overflow":"main",R=D==="hidden",P=D==="overflow"&&f,j=b(C),_=j>=0?j:void 0,W=(0,bl.useRef)(D),ee=(0,bl.useRef)(_),ne=z;ie(()=>{if(ne&&B.current){let M={id:ne,value:C,element:B.current,location:W.current,order:ee.current};return p(M)}},[ne,p,C]),ie(()=>{ne&&g(ne,{element:B.current,location:D,order:_})},[ne,D,_,g]),ie(()=>{m(C,{trigger:B.current})},[m,C]),ie(()=>{var M;!P||A?.overflowActiveValue!==C||(M=B.current)==null||M.focus({preventScroll:!0})},[P,A?.overflowActiveValue,C]);let de=M=>{a?.(M),d(M,C,N)},U=M=>{if(l?.(M),D==="overflow"&&M.key==="Tab"&&M.shiftKey){M.preventDefault(),x(!1);let he=M.currentTarget.ownerDocument.querySelector("[data-overflowbutton]"),Se=c?.requestAnimationFrame;Se?Se(()=>he?.focus({preventScroll:!0})):queueMicrotask(()=>he?.focus({preventScroll:!0}));return}if(D==="overflow"&&A&&(M.key==="ArrowDown"||M.key==="ArrowUp"||M.key==="Home"||M.key==="End")&&A.moveOverflowFocus(M.key,C)){M.preventDefault();return}if(T){(M.key==="Enter"||M.key===" ")&&M.preventDefault();return}(M.key==="Enter"||M.key===" ")&&(M.preventDefault(),d(M,C,N))},me=M=>{var X;i?.(M),ne&&(u.current={value:C,id:ne}),D==="overflow"&&A?.setOverflowActiveValue(C),(X=M.currentTarget.parentElement)==null||X.scrollIntoView({block:"nearest",inline:"nearest"})},ce=Ee(B,n),be=h(C),fe=J_?{"aria-actions":V(O)||void 0}:{},re=D==="overflow"&&A?.overflowActiveValue===C,Z=!(v!==void 0&&y(v)!=null)&&D==="main"&&_===0,se=!R&&(k||I||re||Z),$=D==="overflow"||!T;return(0,vS.jsx)("button",{"aria-selected":I,"aria-disabled":T,"aria-controls":be,...fe,"aria-description":Z_(O.length),tabIndex:se?0:-1,role:"tab",type:"button",onClick:T?void 0:de,onKeyDown:$?U:void 0,onFocus:me,className:V(X_(),o),id:ne,ref:ce,"data-value":C,...s,children:r})});var wS=w(F());var xd=w(E());var Cg=w(F());var Bt=w(E());var gS=`.saltToggleButtonGroup {
  --toggleButtonGroup-borderWidth: var(--salt-size-fixed-100);

  display: flex;
  background: var(--salt-container-primary-background);
  border: var(--toggleButtonGroup-borderWidth) var(--salt-borderStyle-solid) var(--salt-container-bold-borderColor);
  border-radius: var(--salt-palette-corner-weak, 0);
  width: fit-content;
  gap: var(--salt-spacing-50);
  padding: calc(var(--salt-spacing-50) - var(--toggleButtonGroup-borderWidth));
  flex-direction: row;
}

.saltToggleButtonGroup-disabled {
  background: var(--salt-container-primary-background-disabled);
  border-color: var(--salt-container-bold-borderColor-disabled);
  cursor: var(--salt-cursor-disabled);
}

.saltToggleButtonGroup-readOnly {
  background: var(--salt-container-primary-background);
  border-color: var(--salt-container-bold-borderColor);
  cursor: var(--salt-cursor-disabled);
}

.saltToggleButtonGroup .saltToggleButton {
  border-radius: var(--salt-palette-corner-weaker, 0);
}

.saltToggleButtonGroup-horizontal .saltToggleButton {
  height: calc(var(--salt-size-base) - var(--salt-spacing-100));
}

.saltToggleButtonGroup-vertical {
  flex-direction: column;
}

.saltToggleButtonGroup-vertical .saltToggleButton {
  justify-content: start;
}
`;var hS=w(E());var J6=w(F());var Ig=je("ToggleButtonGroupContext",void 0);function bS(){return(0,hS.useContext)(Ig)}var gd=te("saltToggleButtonGroup");function hd(e,t){return Array.isArray(e)&&Array.isArray(t)?e.length===t.length&&e.every((n,r)=>n===t[r]):e===t}var xS=e=>[...e].sort((t,n)=>{let r=t.element.compareDocumentPosition(n.element);return r&Node.DOCUMENT_POSITION_FOLLOWING?-1:r&Node.DOCUMENT_POSITION_PRECEDING?1:0}),e2=(e,t)=>e.length===t.length&&e.every((n,r)=>n===t[r]),Sg=(0,Bt.forwardRef)(function(t,n){let{appearance:r,children:o,className:a,value:l,defaultValue:i,disabled:s,onChange:c,onKeyDown:d,orientation:p="horizontal",readOnly:g,sentiment:m,...b}=t,h=Y();J({testId:"salt-toggle-button-group",css:gS,window:h});let y=(0,Bt.useRef)(null),v=Ee(n,y),[u,f]=Ot({default:i,controlled:l,name:"ToggleButtonGroup",state:"value"}),[x,I]=(0,Bt.useState)(u),[C,k]=(0,Bt.useState)([]),T=(0,Bt.useCallback)((R,P)=>{let j={element:P,value:R};return k(_=>xS([..._.filter(W=>W.element!==P),j])),()=>{k(_=>_.includes(j)?_.filter(W=>W!==j):_)}},[]);ie(()=>{k(R=>{let P=xS(R);return e2(R,P)?R:P})},[o]);let z=(0,Bt.useCallback)((R,...P)=>{let j=P.length===0?R.currentTarget.value:P[0];f(j),hd(u,j)||c?.(R)},[c,u]),O=(0,Bt.useCallback)(R=>hd(u,R),[u]),A=(0,Bt.useCallback)(R=>{I(R)},[]),B=(0,Bt.useCallback)(R=>{if(C.length===0)return x===R||x===void 0||x==="";let P=C.some(j=>hd(j.value,x));return hd(P?x:C[0].value,R)},[x,C]),D=(0,Bt.useMemo)(()=>({appearance:r,disabled:s,focus:A,isFocused:B,isSelected:O,orientation:p,readOnly:g,registerButton:T,select:z,sentiment:m}),[r,s,A,B,O,p,g,T,z,m]),N=R=>{var P,j,_;if(R.altKey||R.ctrlKey||R.metaKey){d?.(R);return}let W=Array.from(((P=y.current)==null?void 0:P.querySelectorAll("button:not([disabled])"))??[]),ee=Xu(y.current),ne=W.indexOf(ee.activeElement);switch(R.key){case"ArrowDown":case"ArrowRight":W.length>0&&(R.preventDefault(),(j=W[(ne+1)%W.length])==null||j.focus());break;case"ArrowUp":case"ArrowLeft":W.length>0&&(R.preventDefault(),(_=W[(ne-1+W.length)%W.length])==null||_.focus());break}d?.(R)};return(0,Cg.jsx)(Ig.Provider,{value:D,children:(0,Cg.jsx)("div",{"aria-disabled":s,"aria-readonly":g,className:V(gd(),gd(p),s&&gd("disabled"),g&&gd("readOnly"),a),role:"radiogroup",ref:v,onKeyDown:N,...b,children:o})})});var yS=`.saltToggleButton {
  --toggleButton-borderWidth: var(--salt-size-fixed-100);

  align-items: center;
  appearance: none;
  background: var(--toggleButton-background);
  border-color: var(--toggleButton-borderColor, transparent);
  border-style: solid;
  border-width: var(--toggleButton-borderWidth);
  border-radius: var(--salt-palette-corner-weak, 0);
  box-sizing: border-box;
  color: var(--toggleButton-text-color);
  cursor: var(--salt-cursor-hover);
  display: inline-flex;
  gap: var(--salt-spacing-50);
  height: var(--salt-size-base);
  justify-content: center;
  line-height: var(--salt-text-lineHeight);
  font-size: var(--salt-text-fontSize);
  font-weight: var(--salt-text-action-fontWeight);
  font-family: var(--salt-text-action-fontFamily);
  letter-spacing: var(--salt-text-action-letterSpacing);
  text-transform: var(--salt-text-action-textTransform);
  padding: 0 calc(var(--salt-spacing-100) - var(--toggleButton-borderWidth));
  margin: 0;
  min-width: unset;
  position: relative;
  text-align: var(--salt-text-action-textAlign);
  text-decoration: none;
  transition: none;
  width: auto;
  -webkit-appearance: none;
  -webkit-tap-highlight-color: transparent;
}

.saltToggleButton:focus-visible {
  outline-style: var(--salt-focused-outlineStyle);
  outline-width: var(--salt-focused-outlineWidth);
  outline-color: var(--salt-focused-outlineColor);
  outline-offset: var(--salt-focused-outlineOffset);
  background: var(--toggleButton-background-hover);
  color: var(--toggleButton-text-color-hover);
  border-color: var(--toggleButton-borderColor-hover);
}

@media (hover: hover) {
  .saltToggleButton:hover {
    background: var(--toggleButton-background-hover);
    color: var(--toggleButton-text-color-hover);
    border-color: var(--toggleButton-borderColor-hover);
  }
}

.saltToggleButton:active {
  background: var(--toggleButton-background-active);
  color: var(--toggleButton-text-color-active);
  border-color: var(--toggleButton-borderColor-active);
}

.saltToggleButton[aria-checked="true"],
.saltToggleButton[aria-pressed="true"] {
  background: var(--toggleButton-background-selected);
  color: var(--toggleButton-text-color-selected);
  cursor: var(--salt-cursor-active);
  border-color: var(--toggleButton-borderColor-selected);
}

.saltToggleButton[aria-checked="true"]:hover {
  cursor: unset;
}

.saltToggleButton[aria-pressed="true"]:hover {
  background: var(--toggleButton-background-selectedHover);
  border-color: var(--toggleButton-borderColor-selectedHover);
}

.saltToggleButton[aria-disabled="true"] {
  background: var(--toggleButton-background);
  color: var(--toggleButton-text-color);
  cursor: var(--salt-cursor-disabled);
  border-color: var(--toggleButton-borderColor);

  opacity: 0.4;
}

.saltToggleButton[aria-checked="true"].saltToggleButton[aria-disabled="true"],
.saltToggleButton[aria-pressed="true"].saltToggleButton[aria-disabled="true"] {
  background: var(--toggleButton-background-selected);
  color: var(--toggleButton-text-color-selected);
  border-color: var(--toggleButton-borderColor-selected);
}

.saltToggleButton.saltToggleButton-readOnly {
  background: var(--toggleButton-background);
  color: var(--toggleButton-text-color);
  cursor: var(--salt-cursor-disabled);
  border-color: var(--toggleButton-borderColor);

  opacity: 0.4;
}

.saltToggleButton[aria-checked="true"].saltToggleButton-readOnly,
.saltToggleButton[aria-pressed="true"].saltToggleButton-readOnly {
  background: var(--toggleButton-background-selected);
  color: var(--toggleButton-text-color-selected);
  border-color: var(--toggleButton-borderColor-selected);

  opacity: unset;
}

.saltToggleButton-neutral.saltToggleButton-solid {
  --toggleButton-text-color: var(--salt-actionable-subtle-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-subtle-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-subtle-foreground-active);
  --toggleButton-text-color-selected: var(--salt-actionable-foreground-selected);
  --toggleButton-background: var(--salt-actionable-subtle-background);
  --toggleButton-background-hover: var(--salt-actionable-subtle-background-hover);
  --toggleButton-background-active: var(--salt-actionable-subtle-background-active);
  --toggleButton-background-selected: var(--salt-actionable-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-subtle-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-subtle-borderColor-hover);
  --toggleButton-borderColor-active: var(--salt-actionable-subtle-borderColor-active);
  --toggleButton-borderColor-selected: var(--salt-actionable-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-bold-background-hover);
}

.saltToggleButton-accented.saltToggleButton-solid {
  --toggleButton-text-color: var(--salt-actionable-accented-subtle-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-accented-subtle-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-accented-subtle-foreground-active);
  --toggleButton-text-color-selected: var(--salt-actionable-accented-foreground-selected);
  --toggleButton-background: var(--salt-actionable-accented-subtle-background);
  --toggleButton-background-hover: var(--salt-actionable-accented-subtle-background-hover);
  --toggleButton-background-active: var(--salt-actionable-accented-subtle-background-active);
  --toggleButton-background-selected: var(--salt-actionable-accented-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-accented-subtle-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-accented-subtle-borderColor-hover);
  --toggleButton-borderColor-active: var(--salt-actionable-accented-subtle-borderColor-active);
  --toggleButton-borderColor-selected: var(--salt-actionable-accented-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-accented-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-accented-bold-background-hover);
}

.saltToggleButton-positive.saltToggleButton-solid {
  --toggleButton-text-color: var(--salt-actionable-positive-subtle-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-positive-subtle-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-positive-subtle-foreground-active);
  --toggleButton-text-color-selected: var(--salt-actionable-positive-foreground-selected);
  --toggleButton-background: var(--salt-actionable-positive-subtle-background);
  --toggleButton-background-hover: var(--salt-actionable-positive-subtle-background-hover);
  --toggleButton-background-active: var(--salt-actionable-positive-subtle-background-active);
  --toggleButton-background-selected: var(--salt-actionable-positive-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-positive-subtle-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-positive-subtle-borderColor-hover);
  --toggleButton-borderColor-active: var(--salt-actionable-positive-subtle-borderColor-active);
  --toggleButton-borderColor-selected: var(--salt-actionable-positive-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-positive-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-accented-bold-background-hover);
}

.saltToggleButton-negative.saltToggleButton-solid {
  --toggleButton-text-color: var(--salt-actionable-negative-subtle-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-negative-subtle-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-negative-subtle-foreground-active);
  --toggleButton-text-color-selected: var(--salt-actionable-negative-foreground-selected);
  --toggleButton-background: var(--salt-actionable-negative-subtle-background);
  --toggleButton-background-hover: var(--salt-actionable-negative-subtle-background-hover);
  --toggleButton-background-active: var(--salt-actionable-negative-subtle-background-active);
  --toggleButton-background-selected: var(--salt-actionable-negative-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-negative-subtle-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-negative-subtle-borderColor-hover);
  --toggleButton-borderColor-active: var(--salt-actionable-negative-subtle-borderColor-active);
  --toggleButton-borderColor-selected: var(--salt-actionable-negative-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-negative-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-negative-bold-background-hover);
}

.saltToggleButton-caution.saltToggleButton-solid {
  --toggleButton-text-color: var(--salt-actionable-caution-subtle-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-caution-subtle-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-caution-subtle-foreground-active);
  --toggleButton-text-color-selected: var(--salt-actionable-caution-foreground-selected);
  --toggleButton-background: var(--salt-actionable-caution-subtle-background);
  --toggleButton-background-hover: var(--salt-actionable-caution-subtle-background-hover);
  --toggleButton-background-active: var(--salt-actionable-caution-subtle-background-active);
  --toggleButton-background-selected: var(--salt-actionable-caution-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-caution-subtle-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-caution-subtle-borderColor-hover);
  --toggleButton-borderColor-active: var(--salt-actionable-caution-subtle-borderColor-active);
  --toggleButton-borderColor-selected: var(--salt-actionable-caution-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-caution-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-caution-bold-background-hover);
}

.saltToggleButton-neutral.saltToggleButton-bordered {
  --toggleButton-text-color: var(--salt-actionable-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-foreground);
  --toggleButton-text-color-selected: var(--salt-actionable-foreground-selected);
  --toggleButton-background: var(--salt-actionable-background);
  --toggleButton-background-hover: var(--salt-actionable-background-hover);
  --toggleButton-background-active: var(--salt-actionable-background);
  --toggleButton-background-selected: var(--salt-actionable-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-borderColor);
  --toggleButton-borderColor-active: var(--salt-actionable-borderColor);
  --toggleButton-borderColor-selected: var(--salt-actionable-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-bold-background-hover);
}

.saltToggleButton-accented.saltToggleButton-bordered {
  --toggleButton-text-color: var(--salt-actionable-accented-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-accented-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-accented-foreground);
  --toggleButton-text-color-selected: var(--salt-actionable-accented-foreground-selected);
  --toggleButton-background: var(--salt-actionable-accented-background);
  --toggleButton-background-hover: var(--salt-actionable-accented-background-hover);
  --toggleButton-background-active: var(--salt-actionable-accented-background);
  --toggleButton-background-selected: var(--salt-actionable-accented-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-accented-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-accented-borderColor);
  --toggleButton-borderColor-active: var(--salt-actionable-accented-borderColor);
  --toggleButton-borderColor-selected: var(--salt-actionable-accented-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-accented-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-accented-bold-background-hover);
}

.saltToggleButton-positive.saltToggleButton-bordered {
  --toggleButton-text-color: var(--salt-actionable-positive-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-positive-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-positive-foreground);
  --toggleButton-text-color-selected: var(--salt-actionable-positive-foreground-selected);
  --toggleButton-background: var(--salt-actionable-positive-background);
  --toggleButton-background-hover: var(--salt-actionable-positive-background-hover);
  --toggleButton-background-active: var(--salt-actionable-positive-background);
  --toggleButton-background-selected: var(--salt-actionable-positive-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-positive-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-positive-borderColor);
  --toggleButton-borderColor-active: var(--salt-actionable-positive-borderColor);
  --toggleButton-borderColor-selected: var(--salt-actionable-positive-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-positive-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-positive-bold-background-hover);
}

.saltToggleButton-negative.saltToggleButton-bordered {
  --toggleButton-text-color: var(--salt-actionable-negative-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-negative-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-negative-foreground);
  --toggleButton-text-color-selected: var(--salt-actionable-negative-foreground-selected);
  --toggleButton-background: var(--salt-actionable-negative-background);
  --toggleButton-background-hover: var(--salt-actionable-negative-background-hover);
  --toggleButton-background-active: var(--salt-actionable-negative-background);
  --toggleButton-background-selected: var(--salt-actionable-negative-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-negative-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-negative-borderColor);
  --toggleButton-borderColor-active: var(--salt-actionable-negative-borderColor);
  --toggleButton-borderColor-selected: var(--salt-actionable-negative-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-negative-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-negative-bold-background-hover);
}

.saltToggleButton-caution.saltToggleButton-bordered {
  --toggleButton-text-color: var(--salt-actionable-caution-foreground);
  --toggleButton-text-color-hover: var(--salt-actionable-caution-foreground-hover);
  --toggleButton-text-color-active: var(--salt-actionable-caution-foreground);
  --toggleButton-text-color-selected: var(--salt-actionable-caution-foreground-selected);
  --toggleButton-background: var(--salt-actionable-caution-background);
  --toggleButton-background-hover: var(--salt-actionable-caution-background-hover);
  --toggleButton-background-active: var(--salt-actionable-caution-background);
  --toggleButton-background-selected: var(--salt-actionable-caution-background-selected);
  --toggleButton-borderColor: var(--salt-actionable-caution-borderColor);
  --toggleButton-borderColor-hover: var(--salt-actionable-caution-borderColor);
  --toggleButton-borderColor-active: var(--salt-actionable-caution-borderColor);
  --toggleButton-borderColor-selected: var(--salt-actionable-caution-borderColor-selected);
  --toggleButton-borderColor-selectedHover: var(--salt-actionable-caution-bold-borderColor-hover);
  --toggleButton-background-selectedHover: var(--salt-actionable-caution-bold-background-hover);
}
`;var bd=te("saltToggleButton"),kg=(0,xd.forwardRef)(function(t,n){let{className:r,props:o}=_n("saltToggleButton",t),{appearance:a,children:l,disabled:i,value:s,onClick:c,onFocus:d,onChange:p,readOnly:g,selected:m,defaultSelected:b,sentiment:h,...y}=o,v=Y();J({testId:"salt-toggle-button",css:yS,window:v});let u=(0,xd.useRef)(null),f=Ee(n,u),x=bS(),I=x?x.isSelected(s):m,C=x?x?.isFocused(s):!0,k=h||x?.sentiment||"neutral",T=a||x?.appearance||"solid",z=x?.disabled||i,O=x?.readOnly||g,A=x?.registerButton;ie(()=>{if(!z&&u.current&&A)return A(s,u.current)},[z,A,s]);let[B,D]=Ot({controlled:I,default:!!b,name:"ToggleButton",state:"selected"}),N=j=>{z||O||(x?.select(j,s),D(!B),p?.(j),c?.(j))},R=j=>{x?.focus(s),d?.(j)},P={"aria-readonly":g,"aria-pressed":x?void 0:B,"aria-checked":x?B:void 0,"aria-disabled":z,role:x?"radio":void 0,className:V(bd(),bd(k),bd(T),O&&bd("readOnly"),r),onClick:N,onFocus:R,tabIndex:C?0:-1,value:s,type:"button",disabled:z,...y};return(0,wS.jsx)("button",{ref:f,...P,children:l})});var Og={};lk(Og,{call:()=>Lg,describeError:()=>d2,fetchMeta:()=>p2,fetchWeekly:()=>f2,getMcp:()=>u2,rowsOf:()=>AS});var Ro="https://ujomxngmefoplrsxmuyf.supabase.co",Eo="sb_publishable_d5Go9QOSznfvLdN2rTwnVw_Ib4aNktm",Tg="cw-session",At=t2(),yd=null,Rg=new Set;function t2(){try{let e=JSON.parse(localStorage.getItem(Tg));return e&&e.access_token&&e.refresh_token?e:null}catch{return null}}function ps(e){At=e;try{e?localStorage.setItem(Tg,JSON.stringify(e)):localStorage.removeItem(Tg)}catch{}for(let t of Rg)t(At)}var IS=()=>At,wd=e=>(Rg.add(e),()=>Rg.delete(e)),He=class extends Error{constructor(t,n){super(n),this.code=t}};function n2(e,t){let n=t.error_code||t.error||"",r=t.msg||t.error_description||t.message||"";return/invalid_credentials|invalid_grant/.test(n)||/Invalid login credentials/i.test(r)?new He("invalid_credentials","\u90AE\u7BB1\u6216\u5BC6\u7801\u4E0D\u5BF9\u3002"):/email_not_confirmed/.test(n)||/Email not confirmed/i.test(r)?new He("email_not_confirmed","\u8FD9\u4E2A\u90AE\u7BB1\u8FD8\u6CA1\u9A8C\u8BC1\uFF1A\u5148\u70B9\u6CE8\u518C\u90AE\u4EF6\u91CC\u7684\u9A8C\u8BC1\u94FE\u63A5\uFF0C\u518D\u56DE\u6765\u767B\u5F55\u3002"):e===429||/rate/i.test(n)?new He("rate_limited","\u5C1D\u8BD5\u6B21\u6570\u592A\u591A\uFF0C\u8FC7\u51E0\u5206\u949F\u518D\u8BD5\u3002"):/refresh_token/i.test(n)||/refresh token/i.test(r)?new He("needs_login","\u767B\u5F55\u5DF2\u8FC7\u671F\uFF0C\u8BF7\u91CD\u65B0\u767B\u5F55\u3002"):new He("auth_error",r||`\u767B\u5F55\u5931\u8D25\uFF08${e}\uFF09\u3002`)}async function CS(e,t){let n;try{n=await fetch(`${Ro}/auth/v1/token?grant_type=${e}`,{method:"POST",headers:{apikey:Eo,"Content-Type":"application/json"},body:JSON.stringify(t)})}catch{throw new He("network","\u8FDE\u4E0D\u4E0A\u6570\u636E\u5E93\u670D\u52A1\u5668\uFF0C\u68C0\u67E5\u7F51\u7EDC\u540E\u518D\u8BD5\u3002")}let r=await n.json().catch(()=>({}));if(!n.ok)throw n2(n.status,r);return{access_token:r.access_token,refresh_token:r.refresh_token,expires_at:r.expires_at||Math.floor(Date.now()/1e3)+(r.expires_in||3600),email:r.user&&r.user.email||t.email||At&&At.email||""}}async function SS(e,t){let n=await CS("password",{email:e.trim().toLowerCase(),password:t});return At=n,n}var Eg=e=>ps(e||At);async function kS(){let e=At;if(At=null,e)try{await fetch(`${Ro}/auth/v1/logout`,{method:"POST",headers:{apikey:Eo,Authorization:`Bearer ${e.access_token}`}})}catch{}}async function r2(){if(!At)throw new He("needs_login","\u8BF7\u5148\u767B\u5F55\u3002");return yd||(yd=CS("refresh_token",{refresh_token:At.refresh_token}).then(e=>(ps(e),e)).catch(e=>{throw e.code!=="network"&&ps(null),e}).finally(()=>{yd=null})),yd}async function Id({force:e=!1}={}){if(!At)throw new He("needs_login","\u8BF7\u5148\u767B\u5F55\u3002");return(e||At.expires_at*1e3-Date.now()<6e4)&&await r2(),At.access_token}async function TS(){let e=At;if(ps(null),!!e)try{await fetch(`${Ro}/auth/v1/logout`,{method:"POST",headers:{apikey:Eo,Authorization:`Bearer ${e.access_token}`}})}catch{}}var RS=()=>location.origin+location.pathname;async function ES(e,t){let n;try{n=await fetch(`${Ro}/auth/v1/signup?redirect_to=${encodeURIComponent(RS())}`,{method:"POST",headers:{apikey:Eo,"Content-Type":"application/json"},body:JSON.stringify({email:e.trim().toLowerCase(),password:t})})}catch{throw new He("network","\u8FDE\u4E0D\u4E0A\u6570\u636E\u5E93\u670D\u52A1\u5668\uFF0C\u68C0\u67E5\u7F51\u7EDC\u540E\u518D\u8BD5\u3002")}let r=await n.json().catch(()=>({}));if(!n.ok){let a=r.error_code||"",l=r.msg||r.error_description||r.message||"";throw/weak_password/.test(a)||/Password should/i.test(l)?new He("weak_password","\u5BC6\u7801\u592A\u77ED\uFF0C\u81F3\u5C11 6 \u4F4D\u3002"):/user_already_exists/.test(a)||/already registered/i.test(l)?new He("exists","\u8FD9\u4E2A\u90AE\u7BB1\u5DF2\u7ECF\u6CE8\u518C\u8FC7\uFF0C\u76F4\u63A5\u767B\u5F55\u5373\u53EF\u3002"):n.status===429||/rate/i.test(a)?new He("rate_limited","\u9A8C\u8BC1\u90AE\u4EF6\u53D1\u5F97\u592A\u9891\u7E41\uFF0C\u8FC7\u4E00\u4F1A\u513F\u518D\u8BD5\u3002"):new He("auth_error",l||`\u6CE8\u518C\u5931\u8D25\uFF08${n.status}\uFF09\u3002`)}if(r.access_token)return{signedIn:!0,session:{access_token:r.access_token,refresh_token:r.refresh_token,expires_at:r.expires_at||Math.floor(Date.now()/1e3)+(r.expires_in||3600),email:e.trim().toLowerCase()}};let o=r.user||r;if(Array.isArray(o.identities)&&o.identities.length===0)throw new He("exists","\u8FD9\u4E2A\u90AE\u7BB1\u5DF2\u7ECF\u6CE8\u518C\u8FC7\uFF0C\u76F4\u63A5\u767B\u5F55\u5373\u53EF\u3002");return{signedIn:!1}}async function PS(e){let t;try{t=await fetch(`${Ro}/auth/v1/recover?redirect_to=${encodeURIComponent(RS())}`,{method:"POST",headers:{apikey:Eo,"Content-Type":"application/json"},body:JSON.stringify({email:e.trim().toLowerCase()})})}catch{throw new He("network","\u8FDE\u4E0D\u4E0A\u6570\u636E\u5E93\u670D\u52A1\u5668\uFF0C\u68C0\u67E5\u7F51\u7EDC\u540E\u518D\u8BD5\u3002")}if(t.status===429)throw new He("rate_limited","\u90AE\u4EF6\u53D1\u5F97\u592A\u9891\u7E41\uFF0C\u8FC7\u4E00\u4F1A\u513F\u518D\u8BD5\u3002");if(!t.ok){let n=await t.json().catch(()=>({}));throw new He("auth_error",n.msg||`\u53D1\u9001\u5931\u8D25\uFF08${t.status}\uFF09\u3002`)}}async function _S(e){let t=await Id(),n=await fetch(`${Ro}/auth/v1/user`,{method:"PUT",headers:{apikey:Eo,Authorization:`Bearer ${t}`,"Content-Type":"application/json"},body:JSON.stringify({password:e})}),r=await n.json().catch(()=>({}));if(!n.ok)throw/weak_password/.test(r.error_code||"")?new He("weak_password","\u5BC6\u7801\u592A\u77ED\uFF0C\u81F3\u5C11 6 \u4F4D\u3002"):/same_password/.test(r.error_code||"")?new He("same_password","\u65B0\u5BC6\u7801\u4E0D\u80FD\u548C\u65E7\u5BC6\u7801\u4E00\u6837\u3002"):new He("auth_error",r.msg||`\u4FEE\u6539\u5931\u8D25\uFF08${n.status}\uFF09\u3002`)}function LS(){let e=new URLSearchParams(location.hash.slice(1)),t=e.get("access_token"),n=e.get("refresh_token"),r=e.get("type")||"",o=e.get("error_description");if(!t&&!o)return null;try{history.replaceState(null,"",location.pathname+location.search)}catch{location.hash=""}if(o)return{error:o.replace(/\+/g," ")};let a="";try{a=JSON.parse(atob(t.split(".")[1].replace(/-/g,"+").replace(/_/g,"/"))).email||""}catch{}return ps({access_token:t,refresh_token:n,expires_at:Number(e.get("expires_at"))||Math.floor(Date.now()/1e3)+Number(e.get("expires_in")||3600),email:a}),{type:r}}var o2=/^\d{2,3}-\d{3}$/,a2=5e3,l2=400,nn=class extends Error{constructor(t,n){super(n),this.code=t}},Cd=e=>e.replace(/[,()*:"'\\%]/g,"").trim(),i2=e=>typeof e=="number"&&Number.isFinite(e)?Number(e.toPrecision(12)):e,Sd=(e,t)=>{let[n,r]=String(e).split("-").map(Number),[o,a]=String(t).split("-").map(Number);return n-o||r-a||String(e).localeCompare(String(t))},OS=(e,t=140)=>{let n=String(e??"");return n.length>t?n.slice(0,t)+"\u2026":n},Pg=(e,t)=>({columns:t,rows:e.map(n=>t.map(r=>i2(n[r]??null)))});function s2(e,t){let n=t.join(""),r=o=>{let a=String(o.name??"");return(o.last_week?4:0)+(a.includes(n)?2:0)+(a.startsWith(t[0])?1:0)};return[...e].sort((o,a)=>r(a)-r(o)||String(o.name??"").length-String(a.name??"").length||Sd(o.indicator_id,a.indicator_id))}function NS(e,t){if(!Array.isArray(e)||!e.length)throw new nn("tool_error","indicator_ids must be a non-empty list");if(e.length>t)throw new nn("tool_error",`at most ${t} indicator_ids per call`);let n=e.map(r=>String(r).trim());if(n.some(r=>!o2.test(r)))throw new nn("tool_error","not indicator IDs");return[...new Set(n)]}async function ur(e,t,n=1e3){let r=[],o=0;for(;r.length<n;){let a=Math.min(1e3,n-r.length+1),l=new URLSearchParams({...t,limit:String(a),offset:String(o)}),i=await BS(`${Ro}/rest/v1/${e}?${l}`);if(r.push(...i),i.length<a)return{rows:r.slice(0,n),truncated:r.length>n};o+=i.length}return{rows:r.slice(0,n),truncated:!0}}async function BS(e,t=!1){let n=await Id(),r;try{r=await fetch(e,{headers:{apikey:Eo,Authorization:`Bearer ${n}`}})}catch{throw new nn("network","\u8FDE\u4E0D\u4E0A\u6570\u636E\u5E93\u670D\u52A1\u5668")}if(r.status===401&&!t)return await Id({force:!0}),BS(e,!0);if(!r.ok)throw new nn(r.status===401?"needs_login":"tool_error",`\u6570\u636E\u5E93\u8BF7\u6C42\u5931\u8D25\uFF08${r.status}\uFF09\uFF1A${(await r.text()).slice(0,200)}`);return r.json()}var c2={async search_indicators(e){let t=String(e.query??"").split(/\s+/).map(Cd).filter(Boolean).slice(0,6);if(!t.length)throw new nn("tool_error","query is empty");let n=Math.max(1,Math.min(50,Number(e.limit??20)||20)),r={select:"indicator_id,module,name,unit,method,coverage_note,last_week",order:"indicator_id",and:`(${t.map(i=>`or(name.ilike.*${i}*,indicator_id.ilike.*${i}*,module.ilike.*${i}*)`).join(",")})`};e.module&&(r.module=`eq.${Cd(String(e.module))}`),r.method=e.method?`eq.${Cd(String(e.method))}`:"neq.excluded";let{rows:o,truncated:a}=await ur("catalog",r,300),l=s2(o,t).slice(0,n);return{matches:a?"300+":o.length,more_available:a||o.length>l.length,...Pg(l.map(i=>({...i,coverage_note:OS(i.coverage_note)})),["indicator_id","module","name","unit","method","coverage_note","last_week"])}},async list_modules(){var n;let{rows:e}=await ur("indicators",{select:"indicator_id,module,method",order:"indicator_id"},3e3);e.sort((r,o)=>Sd(r.indicator_id,o.indicator_id));let t={};for(let r of e)t[n=r.module]??(t[n]={}),t[r.module][r.method]=(t[r.module][r.method]??0)+1;return{modules:Object.entries(t).map(([r,o])=>({module:r,total:Object.values(o).reduce((a,l)=>a+l,0),...o}))}},async describe_indicator(e){let[t]=NS([e.indicator_id],1),n="indicator_id,module,name,definition,unit,source_freq,weekly_rule,source_desc,limits,source_url,method,formula,coverage_note",[r,o]=await Promise.all([ur("indicators",{indicator_id:`eq.${t}`,select:n},1),ur("catalog",{indicator_id:`eq.${t}`,select:"first_week,last_week,ok_weeks"},1)]);if(!r.rows.length)throw new nn("tool_error",`no indicator ${t}`);return{...r.rows[0],...o.rows[0]??{}}},async get_weekly(e){let t=NS(e.indicator_ids,20),n={indicator_id:`in.(${t.join(",")})`,select:"week_cutoff,indicator_id,value,obs_date,status",order:"indicator_id,week_cutoff",status:"eq.ok"},[r,o]=await Promise.all([ur("weekly",n,a2),ur("catalog",{indicator_id:`in.(${t.join(",")})`,select:"indicator_id,name,unit,method,coverage_note"},20)]),a={};for(let l of o.rows)a[l.indicator_id]={name:l.name,unit:l.unit,method:l.method,coverage_note:OS(l.coverage_note,200)};return r.rows.sort((l,i)=>Sd(l.indicator_id,i.indicator_id)),{indicators:a,...Pg(r.rows,["week_cutoff","indicator_id","value","obs_date","status"]),truncated:r.truncated}},async get_latest(e){if(!e.module)throw new nn("tool_error","give module");let{rows:t,truncated:n}=await ur("latest_week",{select:"week_cutoff,indicator_id,module,name,unit,value,obs_date,status,method",order:"indicator_id",module:`eq.${Cd(String(e.module))}`},l2);return t.sort((r,o)=>Sd(r.indicator_id,o.indicator_id)),{week_cutoff:t[0]?.week_cutoff??null,...Pg(t,["indicator_id","module","name","unit","value","obs_date","status","method"]),truncated:n}},async data_status(){let[e,t,n]=await Promise.all([ur("weekly_values",{select:"week_cutoff",order:"week_cutoff.desc"},1),ur("fetch_log",{select:"logged_at",order:"logged_at.desc"},1),ur("latest_week",{select:"status"},3e3)]),r={};for(let o of n.rows)r[o.status]=(r[o.status]??0)+1;if(!e.rows.length&&!n.rows.length)throw new nn("not_reader","\u8FD9\u4E2A\u8D26\u53F7\u4E0D\u5728\u8BFB\u8005\u540D\u5355\u4E0A");return{latest_week:e.rows[0]?.week_cutoff??null,last_fetch:t.rows[0]?.logged_at??null,latest_week_status_counts:r}}},u2=()=>Promise.resolve({web:!0}),_g=new Map;wd(()=>_g.clear());async function Lg(e,t={},{fresh:n=!1}={}){let r=e+JSON.stringify(t),o=_g.get(r);if(o&&!n&&Date.now()-o.at<600*1e3)return o.value;let a=c2[e];if(!a)throw new nn("tool_error",`unknown tool ${e}`);try{let l=await a(t);return _g.set(r,{at:Date.now(),value:l}),l}catch(l){throw l instanceof He?new nn(l.code==="network"?"network":"needs_login",l.message):l}}function d2(e){let t=e&&e.code||"error";switch(t){case"needs_login":return{code:t,title:"\u767B\u5F55\u5DF2\u8FC7\u671F",text:"\u8BF7\u9000\u51FA\u540E\u91CD\u65B0\u767B\u5F55\u3002"};case"not_reader":return{code:t,title:"\u8FD9\u4E2A\u8D26\u53F7\u8FD8\u4E0D\u5728\u8BFB\u8005\u540D\u5355\u4E0A",text:"\u628A\u4F60\u7684\u90AE\u7BB1\u53D1\u7ED9\u7BA1\u7406\u5458\uFF0C\u52A0\u5165\u540D\u5355\u540E\u5237\u65B0\u8FD9\u4E00\u9875\u3002"};case"network":return{code:t,title:"\u8FDE\u4E0D\u4E0A\u6570\u636E\u5E93",text:"\u68C0\u67E5\u7F51\u7EDC\u540E\u70B9\u300C\u91CD\u8BD5\u300D\u3002",canRetry:!0};case"tool_error":return{code:t,title:"\u6570\u636E\u5E93\u62D2\u7EDD\u4E86\u8FD9\u6B21\u67E5\u8BE2",text:e&&e.message||""};default:return{code:t,title:"\u8BFB\u53D6\u6570\u636E\u65F6\u51FA\u9519",text:e&&e.message||"\u7A0D\u540E\u91CD\u8BD5\u3002",canRetry:!0}}}var AS=e=>e&&Array.isArray(e.columns)&&Array.isArray(e.rows)?e.rows.map(t=>Object.fromEntries(e.columns.map((n,r)=>[n,t[r]??null]))):[];async function f2(e){if(!e.length)return[];let t=await Lg("get_weekly",{indicator_ids:e}),n=t&&t.indicators||{};return AS(t).map(r=>{let o=n[r.indicator_id]||{};return{week_cutoff:r.week_cutoff,indicator_id:r.indicator_id,name:o.name??r.indicator_id,unit:o.unit??"",method:o.method??"",coverage_note:o.coverage_note??"",value:r.value==null?null:Number(r.value),obs_date:r.obs_date}})}async function p2(e){let t={};return await Promise.all(e.map(async n=>{try{let r=await Lg("describe_indicator",{indicator_id:n});t[n]={name:r.name||n,unit:r.unit||"",method:r.method||"",coverage_note:r.coverage_note||""}}catch{t[n]={name:n,unit:"",method:"",coverage_note:""}}})),t}var xl=Og,yl=(...e)=>xl.call(...e),FS=(...e)=>xl.describeError(...e),MS=(...e)=>xl.fetchMeta(...e),DS=(...e)=>xl.fetchWeekly(...e),zS=(...e)=>xl.getMcp(...e),Ng=(...e)=>xl.rowsOf(...e);var ms=null;function WS(){return ms||(ms=(async()=>{let e=r=>new URL("vendor/"+r,document.baseURI).href,{default:t}=await import(e("perspective/cdn/perspective.js"));await import(e("perspective-viewer/cdn/perspective-viewer.js")),await Promise.all([import(e("perspective-viewer-datagrid/cdn/perspective-viewer-datagrid.js")),import(e("perspective-viewer-d3fc/cdn/perspective-viewer-d3fc.js"))]),await customElements.whenDefined("perspective-viewer");let n=await t.worker();return{perspective:t,worker:n}})(),ms.catch(()=>{ms=null})),ms}var kd={weekly:{\u65E5\u671F:"date",indicator_id:"string",\u6307\u6807:"string",unit:"string",grp:"string",\u6570\u503C:"float",obs_date:"string",method:"string"},latest:{\u7F16\u53F7:"string",\u6307\u6807:"string",\u6570\u503C:"float",\u5355\u4F4D:"string",\u89C2\u5BDF\u671F:"string",\u72B6\u6001:"string",\u65B9\u5F0F:"string"},coverage:{\u677F\u5757:"string",\u65B9\u5F0F:"string",\u6307\u6807\u6570:"integer"}};function jS(e){let t=()=>{let n=e.querySelector("perspective-viewer-datagrid"),r=n&&(n.regular_table||n.regularTable);return!r||r.__cwMinus?!!(r&&r.__cwMinus):(r.__cwMinus=!0,r.addStyleListener(()=>{for(let o of r.querySelectorAll("td")){let a=o.textContent;a&&a.charCodeAt(0)===45&&/^-[\d.,]+/.test(a)&&(o.textContent="\u2212"+a.slice(1))}}),r.draw&&r.draw(),!0)};t()||setTimeout(t,400)}var VS=["January","February","March","April","May","June","July","August","September","October","November","December"],Bg=VS.map(e=>e.slice(0,3));function m2(e){let t;return(t=VS.indexOf(e))>=0?`${t+1}\u6708`:(t=Bg.indexOf(e))>=0?`${t+1}\u6708`:/^\d{4}$/.test(e)?`${e}\u5E74`:(t=e.match(/^([A-Z][a-z]{2}) (\d{1,2})$/))&&Bg.includes(t[1])?`${Bg.indexOf(t[1])+1}\u6708${+t[2]}\u65E5`:(t=e.match(/^[A-Z][a-z]{2} (\d{1,2})$/))?`${+t[1]}\u65E5`:/^-\d/.test(e)?"\u2212"+e.slice(1):null}var v2=`
  .x-label, .y-label { display: none !important; }
  .legend-container, [class*="legend"] { visibility: hidden !important; pointer-events: none !important; }
  .x-axis text, .y-axis text { font-size: 11px; }
`;function g2(e){let t=e.getBoundingClientRect(),n=[...e.querySelectorAll("g.tick text")].map(a=>{a.style.visibility="";let l=a.getBoundingClientRect();return{t:a,l:l.left,r:l.right,year:/年$/.test(a.textContent)&&!/月/.test(a.textContent)}}).filter(a=>a.r>a.l),r=[],o=a=>a.l>=t.left-1&&a.r<=t.right+1&&r.every(l=>a.r+8<=l.l||a.l>=l.r+8);for(let a of n.filter(l=>l.year))o(a)&&r.push(a);for(let a of n.filter(l=>!l.year))o(a)&&r.push(a);for(let a of n)r.includes(a)||(a.t.style.visibility="hidden")}function Ag(e){let t=e.firstElementChild,n=t&&t.shadowRoot;if(!n||t.localName.indexOf("d3fc")<0)return;if(!n.querySelector("style[data-cw]")){let o=document.createElement("style");o.dataset.cw="1",o.textContent=v2,n.append(o)}let r=()=>{for(let a of n.querySelectorAll(".x-axis text, .y-axis text")){let l=m2(a.textContent);l!=null&&l!==a.textContent&&(a.textContent=l)}let o=n.querySelector(".x-axis svg");o&&t.localName!=="perspective-viewer-d3fc-xbar"&&g2(o)};if(r(),!t.__cwObs){let o=!1;t.__cwObs=new MutationObserver(()=>{o||(o=!0,requestAnimationFrame(()=>{o=!1,r()}))}),t.__cwObs.observe(n,{subtree:!0,childList:!0,characterData:!0})}}var HS={},$S=null;function wl(e){Object.assign(HS,e),clearTimeout($S),$S=setTimeout(async()=>{try{let t=window.claude;if(!t||typeof t.use!="function")return;let[n,r]=await Promise.all([t.use("db"),t.use("user")]),o=r?await r.id():null;if(!n||!o)return;await n.doc(`data/users/${o}/health`).set({...HS,at:new Date().toISOString(),ua:navigator.userAgent.slice(0,160)})}catch{}},1500)}var Fg=/(变动|变化|回报|同比|环比|增速|涨跌|增长)/,h2=/(收益率|利率|利差|SOFR|EFFR|IORB|YTW|通胀率|OAS)/,b2=/(变动|变化|回报|涨跌)/;var Mg=e=>b2.test(e||"");function vs(e,t,n){return e==="bp"||e==="\u767E\u5206\u4F4D"||e==="\u5F20"?0:/汇率/.test(t||"")?4:e==="%"||e==="\u767E\u5206\u70B9"?Fg.test(t||"")?1:2:Math.abs(n)>=1e3?0:2}function Vn(e,t){if(e==null||!Number.isFinite(+e))return"\u2013";let r=new Intl.NumberFormat("en-US",{minimumFractionDigits:t,maximumFractionDigits:t}).format(+e).replace(/^-/,"\u2212");return/^−0(\.0+)?$/.test(r)?r.slice(1):r}var US=e=>e?e==="%"?"%":e==="bp"?" bp":" "+e:"",Td=(e,t,n)=>e==null||!Number.isFinite(+e)?"\u2013":Vn(e,vs(t,n,+e))+US(t);function gs(e,t,n,r){if(e==null||!Number.isFinite(+e))return{text:"\u2013",dir:0};let o=t==="bp"?0:t==="\u4E2A\u767E\u5206\u70B9"?Fg.test(r||"")?1:2:vs(n,r,+e),a=Vn(Math.abs(e),o),i=/^0(\.0+)?$/.test(a.replace(/,/g,""))?0:e>0?1:-1,s=i>0?"+":i<0?"\u2212":"",c=i>0?"\u25B2 ":i<0?"\u25BC ":"",d=t==="\u4E2A\u767E\u5206\u70B9"?" \u4E2A\u767E\u5206\u70B9":US(t);return{text:`${c}${s}${a}${d}`,plain:`${s}${a}${d}`,abs:`${a}${d}`,dir:i}}var Dg=e=>e?new Date(String(e).slice(0,10)+"T00:00:00Z"):null,Po=e=>{let t=Dg(e);return t&&!isNaN(t)?`${t.getUTCFullYear()}\u5E74${t.getUTCMonth()+1}\u6708${t.getUTCDate()}\u65E5`:"\u2013"},KS=e=>{let t=new Date(e);if(!e||isNaN(t))return"\u2013";let n=r=>String(r).padStart(2,"0");return`${t.getFullYear()}\u5E74${t.getMonth()+1}\u6708${t.getDate()}\u65E5 ${n(t.getHours())}:${n(t.getMinutes())}`},GS=e=>e.toISOString().slice(0,10);function qS(e){let t=e.filter(y=>y.value!=null&&Number.isFinite(y.value)).sort((y,v)=>y.week_cutoff<v.week_cutoff?-1:1);if(!t.length)return null;let n=y=>Date.parse(String(y).slice(0,10)+"T00:00:00Z"),r=t[t.length-1],o=r.name||"",a=r.unit==="%"&&h2.test(o)&&!Fg.test(o),l=a?100:1,i=!!r.obs_date&&n(r.week_cutoff)-n(r.obs_date)>10*864e5,s=Mg(o),c=t.find(y=>n(y.week_cutoff)===n(r.week_cutoff)-7*864e5)||null,d=null;if(i){for(let y=t.length-2;y>=0;y--)if(t[y].obs_date!==r.obs_date){d=t[y];break}}let p=n(r.week_cutoff)-364*864e5,g=null;for(let y of t){let v=Math.abs(n(y.week_cutoff)-p);v<=21*864e5&&(!g||v<Math.abs(n(g.week_cutoff)-p))&&(g=y)}let m=a?"bp":r.unit==="%"?"\u4E2A\u767E\u5206\u70B9":r.unit,b=g&&(i||!s)?(r.value-g.value)*l:null,h=/(收益率|利率|利差|OAS)/.test(o);return{last:r,lowFreq:i,flow:s,chgUnit:m,recent:i?d?{label:"\u8F83\u4E0A\u671F",v:(r.value-d.value)*l}:null:!s&&c?{label:"\u8F83\u4E0A\u5468",v:(r.value-c.value)*l}:null,year:b==null?null:{v:b,from:g.week_cutoff},upWord:h?"\u4E0A\u884C":"\u4E0A\u5347",downWord:h?"\u4E0B\u884C":"\u4E0B\u964D"}}function YS(e){if(!e)return"";let{last:t}=e,n=Td(t.value,t.unit,t.name);if(!e.year)return`${t.name}\u6700\u65B0 ${n}`;let r=gs(e.year.v,e.chgUnit,t.unit,t.name);return r.dir===0?`${t.name}\u6700\u65B0 ${n}\uFF0C\u4E0E\u4E00\u5E74\u524D\u6301\u5E73`:`${t.name}\u6700\u65B0 ${n}\uFF0C\u8F83\u4E00\u5E74\u524D${r.dir>0?e.upWord:e.downWord} ${r.abs}`}var zg=e=>String(e||"").replace(/['"`\\\r\n\t]/g," ").replace(/\s+/g," ").trim().slice(0,40),hs={api:"\u63A5\u53E3",proxy:"\u4EE3\u7406",manual:"\u516C\u544A",pending:"\u5F85\u63A5\u5165",excluded:"\u6392\u9664"},Wg={ok:"\u6B63\u5E38",stale:"\u8FC7\u671F",missing_input:"\u7F3A\u539F\u59CB\u6570\u636E",no_vintage:"\u7F3A\u53D1\u5E03\u7248\u672C",insufficient_history:"\u5386\u53F2\u4E0D\u8DB3",provisional:"\u5F85\u751F\u6548",error:"\u51FA\u9519"};var S=w(F()),jg=["12-003","12-007"],Vg=10,Hg=[{v:"1Y",label:"1\u5E74",days:365},{v:"3Y",label:"3\u5E74",days:3*365},{v:"ALL",label:"\u5168\u90E8",days:null}],QS=["trend","week","coverage"],bs={light:["#1e3bd6","#333333","#8a8a8a","#b3b3b3","#6b6b6b","#c9c9c9","#575757","#a0a0a0","#d4d4d4","#7a7a7a"],dark:["#8c9cff","#e0e0e0","#9a9a9a","#6e6e6e","#bdbdbd","#5a5a5a","#cfcfcf","#808080","#4a4a4a","#adadad"]},XS={\u63A5\u53E3:0,\u4EE3\u7406:1,\u516C\u544A:2,\u5F85\u63A5\u5165:3,\u6392\u9664:5},ua={get(e,t){try{return JSON.parse(localStorage.getItem(e))??t}catch{return t}},set(e,t){try{localStorage.setItem(e,JSON.stringify(t))}catch{}}};function x2(){let e=()=>{let r=document.documentElement.getAttribute("data-theme");return r==="dark"||r==="light"?r:window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"},[t,n]=(0,Q.useState)(e);return(0,Q.useEffect)(()=>{let r=window.matchMedia?matchMedia("(prefers-color-scheme: dark)"):null,o=()=>n(e());r&&r.addEventListener("change",o);let a=new MutationObserver(o);return a.observe(document.documentElement,{attributes:!0,attributeFilter:["data-theme"]}),()=>{r&&r.removeEventListener("change",o),a.disconnect()}},[]),t}function Kg(){let e=(0,Q.useRef)(Promise.resolve());return(0,Q.useCallback)(t=>(e.current=e.current.then(t,t).catch(()=>{}),e.current),[])}var ZS=e=>`${e.unit||""}|${Mg(e.name)?"chg":"lvl"}`,Gg=e=>e==="dark"?"Pro Dark":"Pro Light";function Il({error:e,onRetry:t,compact:n}){if(!e)return null;let r=FS(e);return(0,S.jsxs)(mo,{status:r.code==="tool_error"?"error":"warning",className:n?"cw-banner-compact":void 0,children:[(0,S.jsx)(vo,{children:(0,S.jsxs)(Ie,{children:[(0,S.jsx)("strong",{children:r.title}),r.text?`\u3002${r.text}`:""]})}),(r.canAsk||r.canRetry)&&t?(0,S.jsx)(Wv,{children:(0,S.jsx)(Ct,{appearance:"bordered",sentiment:"neutral",onClick:t,children:r.canAsk?"\u5141\u8BB8\u5E76\u52A0\u8F7D":"\u91CD\u8BD5"})}):null]})}function $g({label:e}){return(0,S.jsxs)(wo,{gap:1,align:"center",className:"cw-loading",children:[(0,S.jsx)(ul,{size:"small","aria-label":e}),(0,S.jsx)(Ie,{color:"secondary",children:e})]})}function Ug({c:e,label:t}){return!e||e.text==="\u2013"?(0,S.jsx)("span",{className:"cw-muted",children:"\u2013"}):(0,S.jsxs)("span",{className:e.dir>0?"cw-up":e.dir<0?"cw-down":"cw-flat",children:[t?(0,S.jsx)("span",{className:"cw-chg-label",children:t}):null,e.text]})}function y2({method:e}){return e?(0,S.jsx)("span",{className:`cw-tag cw-tag-${e}`,children:hs[e]||e}):(0,S.jsx)("span",{className:"cw-muted",children:"\u2013"})}function w2({ids:e,onAdd:t,onNotice:n}){let[r,o]=(0,Q.useState)(""),[a,l]=(0,Q.useState)([]),[i,s]=(0,Q.useState)(!1),[c,d]=(0,Q.useState)(null),p=(0,Q.useRef)(0);(0,Q.useEffect)(()=>{let m=zg(r);if(!m){l([]),d(null);return}let b=++p.current,h=setTimeout(async()=>{s(!0);try{let y=await yl("search_indicators",{query:m,limit:30});b===p.current&&(l(Ng(y)),d(null))}catch(y){b===p.current&&(l([]),d(y))}finally{b===p.current&&s(!1)}},280);return()=>clearTimeout(h)},[r]);let g=m=>{if(m){if(!m.last_week){n(`\u300C${m.name}\u300D\u6682\u65E0\u6570\u503C${m.coverage_note?"\uFF1A"+m.coverage_note:""}`);return}t(m.indicator_id,m.name),o(""),l([])}};return(0,S.jsxs)("div",{className:"cw-search",children:[(0,S.jsxs)(Xv,{className:"cw-combo",placeholder:"\u641C\u7D22\u6307\u6807\u5E76\u52A0\u5165\uFF0C\u4F8B\u5982\uFF1A\u7F8E\u56FD 10\u5E74\u3001CPI \u540C\u6BD4\u3001\u9AD8\u6536\u76CA OAS",value:r,onChange:m=>o(m.target.value),selected:[],onSelectionChange:(m,b)=>g(b[b.length-1]),valueToString:m=>m&&m.name||"",startAdornment:(0,S.jsx)(Lu,{"aria-hidden":!0}),endAdornment:i?(0,S.jsx)(ul,{size:"small","aria-label":"\u6B63\u5728\u641C\u7D22"}):null,"aria-label":"\u641C\u7D22\u6307\u6807",children:[a.map(m=>(0,S.jsx)(ts,{value:m,disabled:e.includes(m.indicator_id),children:(0,S.jsxs)("div",{className:"cw-opt",children:[(0,S.jsx)("span",{className:"cw-opt-name",children:m.name}),(0,S.jsxs)("span",{className:"cw-opt-meta",children:[m.indicator_id," \xB7 ",m.module," \xB7 ",m.unit||"\u65E0\u5355\u4F4D"," \xB7 ",hs[m.method]||m.method,e.includes(m.indicator_id)?" \xB7 \u5DF2\u5728\u5217\u8868\u4E2D":m.last_week?` \xB7 \u6700\u8FD1 ${Po(m.last_week)}`:" \xB7 \u6682\u65E0\u6570\u503C"]})]})},m.indicator_id)),r.trim()&&!i&&!a.length&&!c?(0,S.jsx)(ts,{value:null,disabled:!0,children:"\u6CA1\u6709\u5339\u914D\u7684\u6307\u6807\uFF0C\u6362\u4E2A\u5173\u952E\u8BCD\u8BD5\u8BD5"}):null]}),c?(0,S.jsx)(Il,{error:c,compact:!0}):null]})}function I2({ids:e,summaries:t,meta:n,colorOf:r,loading:o,onRemove:a}){return(0,S.jsx)("div",{className:"cw-table-wrap",children:(0,S.jsxs)(og,{className:"cw-table",divider:"tertiary",children:[(0,S.jsx)(lg,{children:(0,S.jsxs)(cd,{children:[(0,S.jsx)(Fr,{children:"\u6307\u6807"}),(0,S.jsx)(Fr,{className:"cw-num",children:"\u6700\u65B0\u503C"}),(0,S.jsx)(Fr,{className:"cw-num",children:"\u8FD1\u671F\u53D8\u5316"}),(0,S.jsx)(Fr,{className:"cw-num",children:"\u8F83\u4E00\u5E74\u524D"}),(0,S.jsx)(Fr,{className:"cw-hide-sm",children:"\u89C2\u5BDF\u671F"}),(0,S.jsx)(Fr,{className:"cw-hide-sm",children:"\u65B9\u5F0F"}),(0,S.jsx)(Fr,{children:(0,S.jsx)("span",{className:"cw-sr",children:"\u79FB\u9664"})})]})}),(0,S.jsx)(ag,{children:e.map(l=>{let i=t[l],s=i?i.last:n[l],c=s&&s.name||l,d=i&&i.recent?gs(i.recent.v,i.chgUnit,i.last.unit,i.last.name):null,p=i&&i.year?gs(i.year.v,i.chgUnit,i.last.unit,i.last.name):null;return(0,S.jsxs)(cd,{children:[(0,S.jsx)(Ar,{children:(0,S.jsxs)("div",{className:"cw-ind",children:[(0,S.jsx)("span",{className:"cw-swatch",style:{background:i?r(l):"transparent"},"aria-hidden":!0}),(0,S.jsxs)("div",{className:"cw-ind-text",children:[(0,S.jsx)("span",{className:"cw-ind-name",children:c}),(0,S.jsxs)("span",{className:"cw-ind-id",children:[l,s&&s.unit?` \xB7 ${s.unit}`:"",i&&i.lowFreq?" \xB7 \u6309\u6708\u6216\u6309\u5B63\u53D1\u5E03":""]})]})]})}),(0,S.jsx)(Ar,{className:"cw-num cw-strong",children:i?Td(i.last.value,i.last.unit,i.last.name):o?"\u2026":"\u2013"}),(0,S.jsx)(Ar,{className:"cw-num",children:i?(0,S.jsx)(Ug,{c:d,label:i.recent?i.recent.label:""}):"\u2013"}),(0,S.jsx)(Ar,{className:"cw-num",children:i?(0,S.jsx)(Ug,{c:p}):"\u2013"}),(0,S.jsx)(Ar,{className:"cw-hide-sm",children:i?Po(i.last.obs_date):!o&&n[l]?(0,S.jsx)("span",{className:"cw-muted",children:"\u6682\u65E0\u5468\u5EA6\u6570\u503C"}):"\u2013"}),(0,S.jsx)(Ar,{className:"cw-hide-sm",children:(0,S.jsx)(y2,{method:s&&s.method})}),(0,S.jsx)(Ar,{className:"cw-act",children:(0,S.jsx)(Ct,{appearance:"transparent",sentiment:"neutral","aria-label":`\u79FB\u9664 ${c}`,disabled:e.length===1,onClick:()=>a(l),children:(0,S.jsx)(Mi,{"aria-hidden":!0})})})]},l)})})]})})}function C2({group:e,psp:t,start:n,mode:r,latestWeek:o}){let a=(0,Q.useRef)(null),l=(0,Q.useRef)(!1),[i,s]=(0,Q.useState)(null),c=vs(e.unit,e.series[0].name,e.series[0].sum?e.series[0].sum.last.value:0),d=(0,Q.useMemo)(()=>e.series.map(u=>u.name).slice().sort((u,f)=>u<f?-1:u>f?1:0),[e]),p=Kg();(0,Q.useEffect)(()=>{let u=a.current;if(!u||!t)return;let f=!0;return p(async()=>{if(f)try{if(l.current||(await u.load(t.tables.weekly),l.current=!0),!f)return;let x=bs[r];d.forEach((I,C)=>{let k=e.series.findIndex(T=>T.name===I);u.style.setProperty(`--d3fc-series-${C+1}`,x[k%x.length])}),u.style.setProperty("--d3fc-series",x[0]),await u.restore({plugin:"Y Line",settings:!1,theme:Gg(r),title:null,group_by:["\u65E5\u671F"],split_by:["\u6307\u6807"],columns:["\u6570\u503C"],aggregates:{\u6570\u503C:"last"},filter:[["grp","==",e.key],...n?[["\u65E5\u671F",">=",n]]:[]],sort:[],expressions:{},columns_config:{\u6570\u503C:{number_format:{minimumFractionDigits:0,maximumFractionDigits:c}}}}),await u.restyleElement(),Ag(u),s(null)}catch(x){f&&s(x)}}),()=>{f=!1}},[t,e.key,d.join("|"),e.series.map(u=>u.id).join(","),n,r,c]);let g=e.series[0].sum,m=e.series.filter(u=>u.method==="proxy"&&u.note),b=[...new Set(e.series.filter(u=>u.method!=="proxy"&&u.note).map(u=>u.note))],h=e.series.filter(u=>u.sum&&u.sum.lowFreq),y=e.kind==="chg"?"\u53D8\u52A8\u4E0E\u56DE\u62A5":"\u6C34\u5E73\u503C",v=e.firstWeek;return(0,S.jsxs)("section",{className:"cw-card cw-chart-card","aria-label":`${e.unit||"\u65E0\u5355\u4F4D"} ${y}`,children:[(0,S.jsxs)(Ie,{styleAs:"label",color:"secondary",className:"cw-overline",children:[e.unit||"\u65E0\u5355\u4F4D"," \xB7 ",y]}),(0,S.jsx)(ed,{className:"cw-chart-title",children:YS(g)}),(0,S.jsxs)(Ie,{color:"secondary",className:"cw-period",children:["\u5468\u4E94\u622A\u70B9\u5468\u5EA6\u503C\uFF08",e.unit||"\u65E0\u5355\u4F4D","\uFF09\uFF0C",v?Po(v):"\u2013","\u2013",Po(o)]}),(0,S.jsx)("div",{className:"cw-legend",children:e.series.map((u,f)=>{let x=u.sum&&u.sum.recent?gs(u.sum.recent.v,u.sum.chgUnit,u.sum.last.unit,u.sum.last.name):null;return(0,S.jsxs)("span",{className:"cw-leg",children:[(0,S.jsx)("span",{className:"cw-leg-line",style:{background:bs[r][f%10]},"aria-hidden":!0}),(0,S.jsx)("span",{children:u.name}),u.sum?(0,S.jsx)("strong",{children:Td(u.sum.last.value,u.sum.last.unit,u.sum.last.name)}):null,x?(0,S.jsx)(Ug,{c:x,label:u.sum.recent.label}):null]},u.id)})}),i?(0,S.jsx)(Il,{error:{code:"upstream_error",message:"\u56FE\u8868\u6CA1\u80FD\u753B\u51FA\u6765\uFF1A"+(i.message||i)},compact:!0}):null,(0,S.jsx)("perspective-viewer",{ref:a,class:"cw-viewer cw-viewer-chart"}),(0,S.jsxs)("div",{className:"cw-notes",children:[b.length?(0,S.jsxs)(Ie,{styleAs:"label",color:"secondary",children:["\u6765\u6E90\uFF1A",b.join("\uFF1B"),"\u3002\u622A\u81F3 ",Po(o),"\u3002"]}):null,m.map(u=>(0,S.jsxs)(Ie,{styleAs:"label",color:"secondary",children:[u.name,"\uFF1A",u.note]},u.id)),h.map(u=>(0,S.jsxs)(Ie,{styleAs:"label",color:"secondary",children:[u.name,"\u6309\u6708\u6216\u6309\u5B63\u53D1\u5E03\uFF0C\u5468\u5EA6\u503C\u6CBF\u7528\u6700\u8FD1\u4E00\u6B21\u53D1\u5E03\uFF1B\u6700\u65B0\u4E00\u671F\u89C2\u5BDF\u671F ",Po(u.sum.last.obs_date),"\uFF08\u8BB0\u5728\u8BE5\u671F\u7B2C\u4E00\u5929\uFF09\uFF0C\u300C\u8F83\u4E0A\u671F\u300D\u6BD4\u7684\u662F\u4E0A\u4E00\u6B21\u53D1\u5E03\u3002"]},u.id+"-obs"))]})]})}function S2({psp:e,module:t,modules:n,onModule:r,rows:o,loading:a,error:l,onRetry:i,mode:s,onPick:c}){let d=(0,Q.useRef)(null),p=(0,Q.useRef)(!1),[g,m]=(0,Q.useState)(""),b=n.filter(y=>y.api+y.proxy+y.manual>0),h=Kg();return(0,Q.useEffect)(()=>{let y=d.current;!y||!e||h(async()=>{p.current||(await y.load(e.tables.latest),p.current=!0,y.addEventListener("perspective-click",v=>{let u=v.detail&&v.detail.row;u&&u.\u7F16\u53F7&&c.current(u.\u7F16\u53F7,u.\u6307\u6807,u.\u72B6\u6001)})),await y.restore({plugin:"Datagrid",settings:!1,theme:Gg(s),title:null,columns:["\u7F16\u53F7","\u6307\u6807","\u6570\u503C","\u5355\u4F4D","\u89C2\u5BDF\u671F","\u72B6\u6001","\u65B9\u5F0F"],group_by:[],split_by:[],sort:[],expressions:{},filter:g?[["\u6307\u6807","contains",g]]:[],columns_config:{\u6570\u503C:{number_fg_mode:"disabled",number_format:{minimumFractionDigits:0,maximumFractionDigits:4}}}}),jS(y)})},[e,s,g]),(0,S.jsxs)(ns,{gap:2,children:[(0,S.jsxs)(wo,{gap:2,align:"end",wrap:!0,className:"cw-toolbar",children:[(0,S.jsxs)("div",{className:"cw-field",children:[(0,S.jsx)(la,{id:"module-label",children:"\u677F\u5757"}),(0,S.jsx)(Jv,{"aria-labelledby":"module-label",className:"cw-dropdown",bordered:!0,value:t,selected:[t],onSelectionChange:(y,v)=>v[0]&&r(v[0]),children:(b.length?b:[{module:t,api:0,proxy:0,manual:0}]).map(y=>(0,S.jsxs)(ts,{value:y.module,children:[y.module,b.length?`\uFF08${y.api+y.proxy+y.manual} \u4E2A\u6709\u6570\uFF09`:""]},y.module))})]}),(0,S.jsxs)("div",{className:"cw-field cw-grow",children:[(0,S.jsx)(la,{id:"filter-label",children:"\u5728\u672C\u677F\u5757\u5185\u7B5B\u9009"}),(0,S.jsx)(hl,{"aria-labelledby":"filter-label",bordered:!0,startAdornment:(0,S.jsx)(Lu,{"aria-hidden":!0}),inputProps:{placeholder:"\u6307\u6807\u540D\u79F0\u91CC\u7684\u5B57\uFF0C\u4F8B\u5982\uFF1A\u6536\u76CA\u7387"},value:g,onChange:y=>m(zg(y.target.value))})]}),(0,S.jsx)(Ie,{color:"secondary",className:"cw-hint",children:"\u70B9\u8868\u683C\u91CC\u7684\u4E00\u884C\uFF0C\u628A\u5B83\u52A0\u5165\u8D70\u52BF\u5206\u6790\u3002\u6708\u5EA6\u3001\u5B63\u5EA6\u6570\u636E\u6CBF\u7528\u6700\u8FD1\u4E00\u6B21\u53D1\u5E03\uFF0C\u4EE5\u300C\u89C2\u5BDF\u671F\u300D\u4E3A\u51C6\u3002"})]}),(0,S.jsx)(Il,{error:l,onRetry:i}),(0,S.jsxs)("div",{className:"cw-card cw-grid-card",children:[a?(0,S.jsx)("div",{className:"cw-overlay",children:(0,S.jsx)($g,{label:"\u6B63\u5728\u8BFB\u53D6\u672C\u5468\u6570\u503C"})}):null,(0,S.jsx)("perspective-viewer",{ref:d,class:"cw-viewer cw-viewer-grid"})]}),(0,S.jsxs)(Ie,{styleAs:"label",color:"secondary",children:[o.length?`\u5171 ${Vn(o.length,0)} \u4E2A\u6307\u6807\uFF1B`:"","\u8868\u5934\u53EF\u6392\u5E8F\uFF1B\u53F3\u4E0A\u89D2\u6309\u94AE\u53EF\u5207\u6362\u6210\u56FE\u8868\u6216\u505A\u900F\u89C6\u5206\u7EC4\u3002"]})]})}function k2({psp:e,modules:t,mode:n}){let r=(0,Q.useRef)(null),o=(0,Q.useRef)(!1),a=(0,Q.useMemo)(()=>{let s={api:0,proxy:0,manual:0,pending:0,excluded:0,total:0};for(let c of t)for(let d of Object.keys(s))s[d]+=c[d]||0;return s},[t]),l=Kg();(0,Q.useEffect)(()=>{let s=r.current;!s||!e||!t.length||l(async()=>{o.current||(await s.load(e.tables.coverage),o.current=!0);let c=bs[n];["\u4EE3\u7406","\u516C\u544A","\u5F85\u63A5\u5165","\u6392\u9664","\u63A5\u53E3"].forEach((d,p)=>s.style.setProperty(`--d3fc-series-${p+1}`,c[XS[d]])),await s.restore({plugin:"X Bar",settings:!1,theme:Gg(n),title:null,group_by:["\u677F\u5757"],split_by:["\u65B9\u5F0F"],columns:["\u6307\u6807\u6570"],aggregates:{\u6307\u6807\u6570:"sum"},sort:[["\u6307\u6807\u6570","desc"]],filter:[],expressions:{}}),await s.restyleElement(),Ag(s)})},[e,t,n]);let i=[["\u63A5\u53E3",a.api,"\u5B98\u65B9\u6216\u514D\u8D39\u63A5\u53E3\u76F4\u53D6\u6216\u6D3E\u751F"],["\u4EE3\u7406",a.proxy,"\u66FF\u4EE3\u6765\u6E90\uFF0C\u8BF4\u660E\u91CC\u5199\u660E\u66FF\u4EE3\u54C1"],["\u516C\u544A",a.manual,"\u4EBA\u5DE5\u7EF4\u62A4\u7684\u5B98\u65B9\u516C\u544A"],["\u5F85\u63A5\u5165",a.pending,"\u6682\u65E0\u514D\u8D39\u6765\u6E90"],["\u6392\u9664",a.excluded,"\u6309\u9700\u6C42\u4E0D\u91C7\u96C6"]];return(0,S.jsxs)(ns,{gap:2,children:[(0,S.jsx)("div",{className:"cw-facts-row",children:i.map(([s,c,d])=>(0,S.jsxs)("div",{className:"cw-fact",children:[(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",children:s}),(0,S.jsx)(Ie,{styleAs:"display3",className:"cw-fact-num",children:Vn(c,0)}),(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",children:d})]},s))}),(0,S.jsxs)("section",{className:"cw-card",children:[(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",className:"cw-overline",children:"\u6307\u6807\u76EE\u5F55 \xB7 \u91C7\u96C6\u65B9\u5F0F"}),(0,S.jsx)(ed,{className:"cw-chart-title",children:a.total?`${Vn(a.total,0)} \u4E2A\u6307\u6807\u91CC ${Vn(a.api+a.proxy+a.manual,0)} \u4E2A\u80FD\u7B97\u51FA\u6570\u503C\uFF0C${Vn(a.pending,0)} \u4E2A\u5F85\u63A5\u5165`:"\u6B63\u5728\u8BFB\u53D6\u76EE\u5F55"}),(0,S.jsx)(Ie,{color:"secondary",className:"cw-period",children:"\u5404\u677F\u5757\u6307\u6807\u6570\uFF0C\u6309\u91C7\u96C6\u65B9\u5F0F\u5206\u6BB5"}),(0,S.jsx)("div",{className:"cw-legend",children:["\u63A5\u53E3","\u4EE3\u7406","\u516C\u544A","\u5F85\u63A5\u5165","\u6392\u9664"].map(s=>(0,S.jsxs)("span",{className:"cw-leg",children:[(0,S.jsx)("span",{className:"cw-leg-box",style:{background:bs[n][XS[s]]},"aria-hidden":!0}),(0,S.jsx)("span",{children:s})]},s))}),(0,S.jsx)("perspective-viewer",{ref:r,class:"cw-viewer cw-viewer-coverage"})]})]})}function T2({mode:e,account:t,onSignOut:n}){let[r,o]=(0,Q.useState)("checking"),[a,l]=(0,Q.useState)(null),[i,s]=(0,Q.useState)(null),[c,d]=(0,Q.useState)([]),[p,g]=(0,Q.useState)(null),[m,b]=(0,Q.useState)(null),[h,y]=(0,Q.useState)(()=>QS.includes(location.hash.slice(1))?location.hash.slice(1):"trend"),[v,u]=(0,Q.useState)(()=>{let L=ua.get("cw-ids",jg);return Array.isArray(L)&&L.length&&L.every(K=>/^\d{2,3}-\d{3}$/.test(K))?L.slice(0,Vg):jg}),[f,x]=(0,Q.useState)(()=>Hg.some(L=>L.v===ua.get("cw-range"))?ua.get("cw-range"):"3Y"),[I,C]=(0,Q.useState)([]),[k,T]=(0,Q.useState)(!1),[z,O]=(0,Q.useState)(null),[A,B]=(0,Q.useState)(!1),[D,N]=(0,Q.useState)({}),[R,P]=(0,Q.useState)(()=>ua.get("cw-module","\u5229\u7387\u4FE1\u7528")),[j,_]=(0,Q.useState)([]),[W,ee]=(0,Q.useState)(!1),[ne,de]=(0,Q.useState)(null),[U,me]=(0,Q.useState)(""),[ce,be]=(0,Q.useState)(0),fe=(0,Q.useRef)(null),re=(0,Q.useCallback)(L=>{me(L),clearTimeout(fe.current),fe.current=setTimeout(()=>me(""),4500)},[]);(0,Q.useEffect)(()=>{ua.set("cw-ids",v)},[v]),(0,Q.useEffect)(()=>{ua.set("cw-range",f)},[f]),(0,Q.useEffect)(()=>{ua.set("cw-module",R)},[R]),(0,Q.useEffect)(()=>{let L=()=>{let K=location.hash.slice(1);QS.includes(K)&&y(K)};return addEventListener("hashchange",L),()=>removeEventListener("hashchange",L)},[]),(0,Q.useEffect)(()=>{zS().then(L=>{o(L?"ready":"absent"),L||wl({mcp:"absent"})})},[]),(0,Q.useEffect)(()=>{WS().then(async({worker:L})=>{let K={weekly:await L.table(kd.weekly),latest:await L.table(kd.latest),coverage:await L.table(kd.coverage)};g({worker:L,tables:K}),wl({perspective:"ok"})}).catch(L=>{b(L),wl({perspective:"error: "+String(L&&L.message||L).slice(0,300)})})},[]),(0,Q.useEffect)(()=>{if(r!=="ready")return;let L=!0;return yl("data_status",{},{fresh:ce>0}).then(K=>{L&&(l(K),s(null),wl({mcp:"ok",latest_week:K&&K.latest_week}))}).catch(K=>{L&&s(K),wl({mcp:"error: "+(K&&K.code||"")+" "+String(K&&K.message||"").slice(0,200)})}),yl("list_modules",{}).then(K=>{L&&d((K.modules||[]).map(oe=>({module:oe.module,total:oe.total||0,api:oe.api||0,proxy:oe.proxy||0,manual:oe.manual||0,pending:oe.pending||0,excluded:oe.excluded||0})))}).catch(()=>{}),()=>{L=!1}},[r,ce]),(0,Q.useEffect)(()=>{if(r!=="ready")return;let L=!0;return T(!0),DS(v).then(async K=>{if(!L)return;C(K),O(null),B(!0);let oe=new Set(K.map(Je=>Je.indicator_id)),pe=v.filter(Je=>!oe.has(Je)&&!D[Je]);if(pe.length){let Je=await MS(pe);L&&N(Hn=>({...Hn,...Je}))}}).catch(K=>L&&O(K)).finally(()=>L&&T(!1)),()=>{L=!1}},[r,v.join(","),ce]),(0,Q.useEffect)(()=>{p&&p.tables.weekly.replace(I.map(L=>({\u65E5\u671F:L.week_cutoff,indicator_id:L.indicator_id,\u6307\u6807:L.name,unit:L.unit,grp:ZS(L),\u6570\u503C:L.value,obs_date:L.obs_date,method:L.method}))).catch(()=>{})},[p,I]),(0,Q.useEffect)(()=>{if(r!=="ready")return;let L=!0;return ee(!0),yl("get_latest",{module:R}).then(K=>{if(!L)return;let oe=Ng(K).map(pe=>({\u7F16\u53F7:pe.indicator_id,\u6307\u6807:pe.name,\u6570\u503C:pe.value==null?null:Number(Vn(pe.value,vs(pe.unit,pe.name,Number(pe.value))).replace(/,/g,"").replace("\u2212","-")),\u5355\u4F4D:pe.unit||"",\u89C2\u5BDF\u671F:pe.obs_date||"",\u72B6\u6001:Wg[pe.status]||pe.status||"",\u65B9\u5F0F:hs[pe.method]||pe.method||""}));_(oe),de(null)}).catch(K=>L&&de(K)).finally(()=>L&&ee(!1)),()=>{L=!1}},[r,R,ce]),(0,Q.useEffect)(()=>{p&&p.tables.latest.replace(j).catch(()=>{})},[p,j]),(0,Q.useEffect)(()=>{if(!p||!c.length)return;let L=[];for(let K of c)for(let[oe,pe]of Object.entries(hs))K[oe]&&L.push({\u677F\u5757:K.module,\u65B9\u5F0F:pe,\u6307\u6807\u6570:K[oe]});p.tables.coverage.replace(L).catch(()=>{})},[p,c]);let G=(0,Q.useCallback)((L,K)=>{u(oe=>oe.includes(L)?(re(`\u300C${K||L}\u300D\u5DF2\u7ECF\u5728\u5217\u8868\u91CC`),oe):oe.length>=Vg?(re(`\u6700\u591A\u540C\u65F6\u770B ${Vg} \u4E2A\u6307\u6807\uFF0C\u5148\u79FB\u9664\u4E00\u4E2A`),oe):(re(`\u5DF2\u52A0\u5165\uFF1A${K||L}`),[...oe,L]))},[re]),Z=(0,Q.useCallback)(L=>u(K=>K.length>1?K.filter(oe=>oe!==L):K),[]),se=(0,Q.useRef)(null);se.current=(L,K,oe)=>{if(oe&&oe!==Wg.ok){re(`\u300C${K}\u300D\u672C\u5468\u6CA1\u6709\u53EF\u7528\u6570\u503C\uFF08${oe}\uFF09`);return}G(L,K)};let $=a&&a.latest_week||I.reduce((L,K)=>K.week_cutoff>L?K.week_cutoff:L,""),M=(0,Q.useMemo)(()=>{var oe;let L={};for(let pe of I)(L[oe=pe.indicator_id]||(L[oe]=[])).push(pe);let K={};for(let[pe,Je]of Object.entries(L))K[pe]=qS(Je);return K},[I]),X=(0,Q.useMemo)(()=>{let L=Hg.find(K=>K.v===f);return!L||!L.days||!$?null:GS(new Date(Dg($).getTime()-L.days*864e5))},[f,$]),he=(0,Q.useMemo)(()=>{let L=new Map;for(let K of v){let oe=M[K];if(!oe)continue;let pe=ZS(oe.last);L.has(pe)||L.set(pe,{key:pe,unit:oe.last.unit,kind:pe.endsWith("|chg")?"chg":"lvl",series:[]}),L.get(pe).series.push({id:K,name:oe.last.name,method:oe.last.method,note:oe.last.coverage_note,sum:oe})}for(let K of L.values()){let oe=I.filter(pe=>K.series.some(Je=>Je.id===pe.indicator_id)&&pe.value!=null&&(!X||pe.week_cutoff>=X)).map(pe=>pe.week_cutoff);K.firstWeek=oe.length?oe.reduce((pe,Je)=>pe<Je?pe:Je):null}return[...L.values()]},[v,M,I,X]),Se=(0,Q.useCallback)(L=>{for(let K of he){let oe=K.series.findIndex(pe=>pe.id===L);if(oe>=0)return bs[e][oe%10]}return"transparent"},[he,e]),ge=A&&!z&&!k?v.filter(L=>!M[L]):[],ve=a&&a.latest_week_status_counts?a.latest_week_status_counts:null,we=ve?Object.values(ve).reduce((L,K)=>L+K,0):null,ye=r==="ready"&&i&&z&&ne&&(i.code||"")===(z.code||"")?i:null,_e=()=>be(L=>L+1);return(0,S.jsxs)("div",{className:"cw-page",children:[(0,S.jsxs)("header",{className:"cw-head",children:[(0,S.jsxs)("div",{className:"cw-brand",children:[(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",className:"cw-eyebrow",children:"Capital Weekly \xB7 \u5468\u62A5\u6570\u636E\u5E93"}),(0,S.jsx)(Zi,{className:"cw-title",children:"\u8D44\u672C\u5E02\u573A\u5468\u62A5\u6570\u636E\u53F0"})]}),(0,S.jsxs)("dl",{className:"cw-facts","aria-label":"\u6570\u636E\u65B0\u9C9C\u5EA6",children:[(0,S.jsxs)("div",{children:[(0,S.jsx)("dt",{children:"\u6570\u636E\u622A\u81F3"}),(0,S.jsx)("dd",{children:a?`${Po(a.latest_week)}\uFF08\u5468\u4E94\uFF09`:"\u2026"})]}),(0,S.jsxs)("div",{children:[(0,S.jsx)("dt",{children:"\u672C\u5468\u6709\u503C"}),(0,S.jsx)("dd",{children:ve?`${Vn(ve.ok||0,0)} / ${Vn(we,0)}`:"\u2026"})]}),(0,S.jsxs)("div",{children:[(0,S.jsx)("dt",{children:"\u6700\u8FD1\u6293\u53D6"}),(0,S.jsx)("dd",{children:a?KS(a.last_fetch):"\u2026"})]}),t?(0,S.jsxs)("div",{children:[(0,S.jsx)("dt",{children:"\u8D26\u53F7"}),(0,S.jsx)("dd",{className:"cw-account",children:t})]}):null,(0,S.jsxs)("div",{className:"cw-refresh",children:[(0,S.jsx)(Ct,{appearance:"transparent",sentiment:"neutral",onClick:_e,"aria-label":"\u91CD\u65B0\u8BFB\u53D6\u6570\u636E",children:(0,S.jsx)(bv,{"aria-hidden":!0})}),n?(0,S.jsx)(Ct,{appearance:"bordered",sentiment:"neutral",onClick:n,children:"\u9000\u51FA"}):null]})]})]}),r==="absent"?(0,S.jsx)(mo,{status:"warning",children:(0,S.jsx)(vo,{children:(0,S.jsxs)(Ie,{children:[(0,S.jsx)("strong",{children:"\u8FD9\u4E2A\u9875\u9762\u8981\u5728 Claude \u91CC\u6253\u5F00\u624D\u80FD\u8BFB\u53D6\u6570\u636E\u5E93\u3002"}),"\u7528 Claude \u7F51\u9875\u7248\u6216\u684C\u9762\u7248\u6253\u5F00\u5B83\uFF0C\u5E76\u5728 \u8BBE\u7F6E \u2192 \u8FDE\u63A5\u5668 \u91CC\u63A5\u4E0A\u300C\u91D1\u878D\u6570\u636E\u5E93\u300D\u3002"]})})}):null,ye?(0,S.jsx)(Il,{error:ye,onRetry:_e}):null,!ye&&i&&["not_reader","needs_login"].includes(i.code)?(0,S.jsx)(Il,{error:i}):null,m?(0,S.jsx)(mo,{status:"error",children:(0,S.jsx)(vo,{children:(0,S.jsxs)(Ie,{children:[(0,S.jsx)("strong",{children:"\u8868\u683C\u548C\u56FE\u8868\u7EC4\u4EF6\u6CA1\u80FD\u52A0\u8F7D\u3002"}),String(m.message||m),"\u3002\u5237\u65B0\u9875\u9762\u518D\u8BD5\u4E00\u6B21\u3002"]})})}):null,(0,S.jsxs)(wg,{value:h,onChange:(L,K)=>{y(K);try{history.replaceState(null,"","#"+K)}catch{location.hash=K}},children:[(0,S.jsx)(dg,{divider:!0,children:(0,S.jsxs)(xg,{"aria-label":"\u89C6\u56FE",children:[(0,S.jsx)(os,{value:"trend",children:(0,S.jsx)(fs,{children:"\u8D70\u52BF\u5206\u6790"})}),(0,S.jsx)(os,{value:"week",children:(0,S.jsx)(fs,{children:"\u672C\u5468\u4E00\u89C8"})}),(0,S.jsx)(os,{value:"coverage",children:(0,S.jsx)(fs,{children:"\u8986\u76D6\u60C5\u51B5"})})]})}),(0,S.jsx)(ds,{value:"trend",className:"cw-panel",children:(0,S.jsxs)(ns,{gap:2,children:[(0,S.jsxs)(wo,{gap:2,align:"end",justify:"space-between",wrap:!0,className:"cw-toolbar",children:[(0,S.jsx)(w2,{ids:v,onAdd:G,onNotice:re}),(0,S.jsxs)(wo,{gap:1,align:"center",className:"cw-range",children:[(0,S.jsx)(la,{id:"range-label",children:"\u533A\u95F4"}),(0,S.jsx)(Sg,{"aria-labelledby":"range-label",value:f,onChange:L=>x(L.currentTarget.value),children:Hg.map(L=>(0,S.jsx)(kg,{value:L.v,children:L.label},L.v))}),(0,S.jsx)(Ct,{appearance:"transparent",sentiment:"neutral",onClick:()=>{u(jg),x("3Y"),re("\u5DF2\u6062\u590D\u9ED8\u8BA4")},children:"\u6062\u590D\u9ED8\u8BA4"})]})]}),ye?null:(0,S.jsx)(Il,{error:z,onRetry:_e}),(0,S.jsx)(I2,{ids:v,summaries:M,meta:D,colorOf:Se,loading:k,onRemove:Z}),ge.length?(0,S.jsxs)(Ie,{color:"secondary",className:"cw-hint",children:[ge.map(L=>D[L]&&D[L].name||L).join("\u3001"),"\u6682\u65E0\u5468\u5EA6\u6570\u503C",ge.length===1&&D[ge[0]]&&D[ge[0]].coverage_note?`\uFF1A${D[ge[0]].coverage_note}`:"\uFF08\u591A\u4E3A\u5C1A\u672A\u63A5\u5165\u7684\u6570\u636E\u6E90\uFF09","\u3002"]}):null,r==="ready"&&k&&!I.length?(0,S.jsx)($g,{label:"\u6B63\u5728\u8BFB\u53D6\u5468\u5EA6\u5E8F\u5217"}):null,!p&&!m?(0,S.jsx)($g,{label:"\u6B63\u5728\u52A0\u8F7D Perspective"}):null,(0,S.jsx)("div",{className:"cw-charts",children:he.map(L=>(0,S.jsx)(C2,{group:L,psp:p,start:X,mode:e,latestWeek:$},L.key))})]})}),(0,S.jsx)(ds,{value:"week",className:"cw-panel",children:(0,S.jsx)(S2,{psp:p,module:R,modules:c,onModule:P,rows:j,loading:W,error:ye?null:ne,onRetry:_e,mode:e,onPick:se})}),(0,S.jsx)(ds,{value:"coverage",className:"cw-panel",children:(0,S.jsx)(k2,{psp:p,modules:c,mode:e})})]}),(0,S.jsxs)("footer",{className:"cw-foot",children:[(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",children:"\u65B9\u5F0F\uFF1A\u63A5\u53E3\uFF1D\u5B98\u65B9\u6216\u514D\u8D39\u63A5\u53E3\uFF1B\u4EE3\u7406\uFF1D\u66FF\u4EE3\u6765\u6E90\uFF08\u8BF4\u660E\u91CC\u5199\u660E\u66FF\u4EE3\u54C1\uFF0C\u5F15\u7528\u65F6\u6CE8\u660E\uFF09\uFF1B\u516C\u544A\uFF1D\u4EBA\u5DE5\u7EF4\u62A4\u7684\u5B98\u65B9\u516C\u544A\uFF1B\u5F85\u63A5\u5165\uFF1D\u6682\u65E0\u514D\u8D39\u6765\u6E90\uFF0C\u6CA1\u6709\u6570\u503C\u3002\u56FE\u91CC\u53EA\u753B\u72B6\u6001\u6B63\u5E38\u7684\u5468\u5EA6\u503C\uFF0C\u7F3A\u53E3\u7559\u7A7A\uFF0C\u4E0D\u63D2\u503C\u3002"}),(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",children:"MSCI\u3001ISM\u3001S&P Global \u7B49\u6570\u636E\u4EC5\u4F9B\u540D\u5355\u5185\u540C\u5B66\u5B66\u4E60\u4F7F\u7528\uFF0C\u4E0D\u8981\u5BFC\u51FA\u6574\u8868\u8F6C\u7ED9\u540D\u5355\u5916\u7684\u4EBA\u3002\u754C\u9762\u7528 J.P. Morgan \u5F00\u6E90\u7684 Salt \u8BBE\u8BA1\u7CFB\u7EDF\uFF0C\u8868\u683C\u548C\u56FE\u8868\u7528 FINOS Perspective\uFF08\u539F J.P. Morgan \u5F00\u6E90\uFF09\u3002"})]}),(0,S.jsx)("div",{className:"cw-toast",role:"status","aria-live":"polite",hidden:!U,children:U})]})}var R2="\u70B9\u90AE\u4EF6\u91CC\u7684\u94FE\u63A5\u5B8C\u6210\u9A8C\u8BC1\uFF0C\u7136\u540E\u56DE\u5230\u8FD9\u4E2A\u7F51\u5740\u767B\u5F55\u3002";function E2({notice:e}){let[t,n]=(0,Q.useState)("login"),[r,o]=(0,Q.useState)(""),[a,l]=(0,Q.useState)(""),[i,s]=(0,Q.useState)(!1),[c,d]=(0,Q.useState)(""),[p,g]=(0,Q.useState)(e||""),m=v=>{n(v),d(""),g("")},b=async()=>{try{await yl("data_status",{},{fresh:!0}),Eg()}catch(v){await kS(),d(v.code==="not_reader"?"\u8FD9\u4E2A\u8D26\u53F7\u8FD8\u4E0D\u5728\u8BFB\u8005\u540D\u5355\u4E0A\u3002\u628A\u4F60\u7684\u90AE\u7BB1\u53D1\u7ED9\u7BA1\u7406\u5458\uFF0C\u52A0\u5165\u540D\u5355\u540E\u518D\u767B\u5F55\u3002":v.message||"\u767B\u5F55\u540E\u8BFB\u53D6\u6570\u636E\u5931\u8D25\u3002")}};return(0,S.jsx)("div",{className:"cw-login",children:(0,S.jsxs)("div",{className:"cw-login-card",children:[(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",className:"cw-eyebrow",children:"Capital Weekly \xB7 \u5468\u62A5\u6570\u636E\u5E93"}),(0,S.jsx)(Zi,{className:"cw-title",children:"\u8D44\u672C\u5E02\u573A\u5468\u62A5\u6570\u636E\u53F0"}),(0,S.jsx)(Ie,{color:"secondary",children:t==="signup"?"\u7528\u4F60\u7684\u90AE\u7BB1\u6CE8\u518C\u5E76\u81EA\u5DF1\u8BBE\u4E00\u4E2A\u5BC6\u7801\uFF08\u81F3\u5C11 6 \u4F4D\uFF09\u3002\u6CE8\u518C\u540E\u8981\u70B9\u9A8C\u8BC1\u90AE\u4EF6\u91CC\u7684\u94FE\u63A5\uFF1B\u53EA\u6709\u8BFB\u8005\u540D\u5355\u4E0A\u7684\u90AE\u7BB1\u80FD\u770B\u5230\u6570\u636E\u3002":t==="reset"?"\u586B\u4F60\u6CE8\u518C\u7528\u7684\u90AE\u7BB1\uFF0C\u6211\u4EEC\u4F1A\u53D1\u4E00\u5C01\u91CD\u8BBE\u5BC6\u7801\u7684\u90AE\u4EF6\u3002":"\u7528\u8BFB\u8005\u540D\u5355\u4E0A\u7684\u90AE\u7BB1\u767B\u5F55\u3002\u7B2C\u4E00\u6B21\u7528\u8BF7\u5148\u6CE8\u518C\u3002"}),(0,S.jsxs)("form",{className:"cw-login-form",onSubmit:async v=>{if(v.preventDefault(),d(""),g(""),!r.trim()){d("\u8BF7\u586B\u5199\u90AE\u7BB1\u3002");return}if(t!=="reset"&&!a){d("\u8BF7\u586B\u5199\u5BC6\u7801\u3002");return}if(t==="signup"&&a.length<6){d("\u5BC6\u7801\u81F3\u5C11 6 \u4F4D\u3002");return}s(!0);try{if(t==="login")await SS(r,a),await b();else if(t==="signup"){let u=await ES(r,a);u.signedIn?Eg(u.session):(n("login"),l(""),g(`\u9A8C\u8BC1\u90AE\u4EF6\u5DF2\u53D1\u5230 ${r.trim()}\u3002${R2}`))}else await PS(r),n("login"),g(`\u91CD\u8BBE\u5BC6\u7801\u7684\u90AE\u4EF6\u5DF2\u53D1\u5230 ${r.trim()}\uFF0C\u70B9\u90AE\u4EF6\u91CC\u7684\u94FE\u63A5\u8BBE\u7F6E\u65B0\u5BC6\u7801\u3002`)}catch(u){d(u.message||"\u64CD\u4F5C\u5931\u8D25\u3002")}finally{s(!1)}},noValidate:!0,children:[(0,S.jsx)(Zv,{className:"cw-login-h",children:t==="signup"?"\u6CE8\u518C\u8D26\u53F7":t==="reset"?"\u91CD\u8BBE\u5BC6\u7801":"\u767B\u5F55"}),(0,S.jsxs)(es,{children:[(0,S.jsx)(ia,{children:"\u90AE\u7BB1"}),(0,S.jsx)(hl,{bordered:!0,value:r,onChange:v=>o(v.target.value),inputProps:{id:"email",name:"email",type:"email",autoComplete:"username",inputMode:"email"}})]}),t!=="reset"?(0,S.jsxs)(es,{children:[(0,S.jsx)(ia,{children:t==="signup"?"\u8BBE\u7F6E\u5BC6\u7801":"\u5BC6\u7801"}),(0,S.jsx)(hl,{bordered:!0,value:a,onChange:v=>l(v.target.value),inputProps:{id:"password",name:"password",type:"password",autoComplete:t==="signup"?"new-password":"current-password"}})]}):null,c?(0,S.jsx)(mo,{status:"error",children:(0,S.jsx)(vo,{children:(0,S.jsx)(Ie,{children:c})})}):null,p?(0,S.jsx)(mo,{status:"success",children:(0,S.jsx)(vo,{children:(0,S.jsx)(Ie,{children:p})})}):null,(0,S.jsx)(Ct,{type:"submit",sentiment:"accented",appearance:"solid",disabled:i,children:i?"\u8BF7\u7A0D\u5019\u2026":t==="signup"?"\u6CE8\u518C":t==="reset"?"\u53D1\u9001\u91CD\u8BBE\u90AE\u4EF6":"\u767B\u5F55"})]}),(0,S.jsxs)("div",{className:"cw-login-links",children:[t!=="login"?(0,S.jsx)(Ct,{appearance:"transparent",sentiment:"neutral",onClick:()=>m("login"),children:"\u8FD4\u56DE\u767B\u5F55"}):null,t!=="signup"?(0,S.jsx)(Ct,{appearance:"transparent",sentiment:"neutral",onClick:()=>m("signup"),children:"\u7B2C\u4E00\u6B21\u7528\uFF1F\u6CE8\u518C\u8D26\u53F7"}):null,t==="login"?(0,S.jsx)(Ct,{appearance:"transparent",sentiment:"neutral",onClick:()=>m("reset"),children:"\u5FD8\u8BB0\u5BC6\u7801"}):null]}),(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",children:"MSCI\u3001ISM\u3001S&P Global \u7B49\u6570\u636E\u4EC5\u4F9B\u540D\u5355\u5185\u540C\u5B66\u5B66\u4E60\u4F7F\u7528\u3002"})]})})}function P2({onDone:e}){let[t,n]=(0,Q.useState)(""),[r,o]=(0,Q.useState)(!1),[a,l]=(0,Q.useState)("");return(0,S.jsx)("div",{className:"cw-login",children:(0,S.jsxs)("div",{className:"cw-login-card",children:[(0,S.jsx)(Ie,{styleAs:"label",color:"secondary",className:"cw-eyebrow",children:"Capital Weekly \xB7 \u5468\u62A5\u6570\u636E\u5E93"}),(0,S.jsx)(Zi,{className:"cw-title",children:"\u8BBE\u7F6E\u65B0\u5BC6\u7801"}),(0,S.jsxs)("form",{className:"cw-login-form",onSubmit:async s=>{if(s.preventDefault(),t.length<6){l("\u5BC6\u7801\u81F3\u5C11 6 \u4F4D\u3002");return}o(!0),l("");try{await _S(t),e()}catch(c){l(c.message||"\u4FEE\u6539\u5931\u8D25\u3002")}finally{o(!1)}},noValidate:!0,children:[(0,S.jsxs)(es,{children:[(0,S.jsx)(ia,{children:"\u65B0\u5BC6\u7801\uFF08\u81F3\u5C11 6 \u4F4D\uFF09"}),(0,S.jsx)(hl,{bordered:!0,value:t,onChange:s=>n(s.target.value),inputProps:{id:"new-password",name:"new-password",type:"password",autoComplete:"new-password"}})]}),a?(0,S.jsx)(mo,{status:"error",children:(0,S.jsx)(vo,{children:(0,S.jsx)(Ie,{children:a})})}):null,(0,S.jsx)(Ct,{type:"submit",sentiment:"accented",appearance:"solid",disabled:r,children:r?"\u8BF7\u7A0D\u5019\u2026":"\u4FDD\u5B58\u65B0\u5BC6\u7801"})]})]})})}function _2({mode:e}){let[t]=(0,Q.useState)(()=>LS()),[n,r]=(0,Q.useState)(IS),[o,a]=(0,Q.useState)(()=>!!(t&&t.type==="recovery"));return(0,Q.useEffect)(()=>wd(r),[]),n?o?(0,S.jsx)(P2,{onDone:()=>a(!1)}):(0,S.jsx)(T2,{mode:e,account:n.email,onSignOut:()=>TS()}):(0,S.jsx)(E2,{notice:t&&t.error?`\u94FE\u63A5\u65E0\u6548\u6216\u5DF2\u8FC7\u671F\uFF1A${t.error}`:""})}function L2(){let e=x2();return(0,S.jsx)(Li,{mode:e,accent:"blue",corner:"sharp",headingFont:"Open Sans",actionFont:"Open Sans",density:"medium",applyClassesTo:"root",children:(0,S.jsx)(_2,{mode:e})})}(0,JS.createRoot)(document.getElementById("app")).render((0,S.jsx)(L2,{}));})();
/*! Bundled license information:

react/cjs/react.production.min.js:
  (**
   * @license React
   * react.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

scheduler/cjs/scheduler.production.min.js:
  (**
   * @license React
   * scheduler.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

react-dom/cjs/react-dom.production.min.js:
  (**
   * @license React
   * react-dom.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

react/cjs/react-jsx-runtime.production.min.js:
  (**
   * @license React
   * react-jsx-runtime.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

use-sync-external-store/cjs/use-sync-external-store-shim.production.js:
  (**
   * @license React
   * use-sync-external-store-shim.production.js
   *
   * Copyright (c) Meta Platforms, Inc. and affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

tabbable/dist/index.esm.js:
  (*!
  * tabbable 6.5.0
  * @license MIT, https://github.com/focus-trap/tabbable/blob/master/LICENSE
  *)
*/
