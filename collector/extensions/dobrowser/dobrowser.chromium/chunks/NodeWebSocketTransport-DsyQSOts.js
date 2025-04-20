
!function(){try{var e="undefined"!=typeof window?window:"undefined"!=typeof global?global:"undefined"!=typeof self?self:{},n=(new e.Error).stack;n&&(e._sentryDebugIds=e._sentryDebugIds||{},e._sentryDebugIds[n]="44c66389-5c6e-5991-9731-4682dc4fdbd1")}catch(e){}}();
var u=Object.defineProperty;var c=s=>{throw TypeError(s)};var g=(s,e,t)=>e in s?u(s,e,{enumerable:!0,configurable:!0,writable:!0,value:t}):s[e]=t;var i=(s,e,t)=>g(s,typeof e!="symbol"?e+"":e,t),d=(s,e,t)=>e.has(s)||c("Cannot "+t);var o=(s,e,t)=>(d(s,e,"read from private field"),t?t.call(s):e.get(s)),h=(s,e,t)=>e.has(s)?c("Cannot add the same private member more than once"):e instanceof WeakSet?e.add(s):e.set(s,t),m=(s,e,t,r)=>(d(s,e,"write to private field"),r?r.call(s,t):e.set(s,t),t);import{N as w}from"./browser-UNYYHaua.js";import{p as v}from"./index-CNkQF85e.js";import"./Providers-CszSossT.js";/**
 * @license
 * Copyright 2018 Google Inc.
 * SPDX-License-Identifier: Apache-2.0
 */var n;const l=class l{constructor(e){h(this,n);i(this,"onmessage");i(this,"onclose");m(this,n,e),o(this,n).addEventListener("message",t=>{this.onmessage&&this.onmessage.call(null,t.data)}),o(this,n).addEventListener("close",()=>{this.onclose&&this.onclose.call(null)}),o(this,n).addEventListener("error",()=>{})}static create(e,t){return new Promise((r,f)=>{const a=new w(e,[],{followRedirects:!0,perMessageDeflate:!1,allowSynchronousEvents:!1,maxPayload:268435456,headers:{"User-Agent":`Puppeteer ${v}`,...t}});a.addEventListener("open",()=>r(new l(a))),a.addEventListener("error",f)})}send(e){o(this,n).send(e)}close(){o(this,n).close()}};n=new WeakMap;let p=l;export{p as NodeWebSocketTransport};
//# sourceMappingURL=NodeWebSocketTransport-DsyQSOts.js.map

//# debugId=44c66389-5c6e-5991-9731-4682dc4fdbd1
