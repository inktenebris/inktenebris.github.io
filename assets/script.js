"use strict";

if(
typeof gsap !== "undefined" &&
typeof ScrollTrigger !== "undefined"
){
gsap.registerPlugin(
ScrollTrigger
);
}

/* ========================================
LOADER
======================================== */
window.addEventListener("load", () => {
const loader =
document.getElementById("loader");

if(!loader) return;

setTimeout(()=>{
loader.style.display="none";
},3000);

if(typeof gsap !== "undefined"){
const tl = gsap.timeline();

tl.to("#loader span",{
opacity:1,
duration:.4
})
.to(loader,{
opacity:0,
duration:.5,
delay:.2,
onComplete:()=>{
loader.style.display="none";
}
});
}
});

/* ========================================
DOM ELEMENTS
======================================== */
const nav = document.querySelector("nav");
const heroImage = document.querySelector(".hero-image");
const heroTitle = document.querySelector(".hero-title");
const transition = document.getElementById("page-transition");
const sections = document.querySelectorAll("section[id]");
const revealItems = document.querySelectorAll(".artwork");

/* ========================================
INTERSECTION OBSERVER
======================================== */
const observer = new IntersectionObserver(
entries => {
entries.forEach(entry => {
if (entry.isIntersecting) {
entry.target.classList.add("show");
observer.unobserve(entry.target);
}
});
},
{
threshold: 0.1,
rootMargin: "0px 0px -80px 0px"
}
);
revealItems.forEach(item => observer.observe(item));

/* ========================================
GSAP SCROLL REVEALS
======================================== */
if (
typeof gsap !== "undefined" &&
typeof ScrollTrigger !== "undefined"
)
{
gsap.utils.toArray(
".intro, .split-showcase, .exhibition-intro, .manifesto, #about, #instagram, #contact, #updates, .fullscreen-artwork"
).forEach(section => {
gsap.from(section, {
opacity: 0,
y: 60,
duration: 0.8,
ease: "power4.out",
scrollTrigger: {
trigger: section,
start: "top 85%"
}
});
});
}

/* ========================================
GLOBAL SCROLL EFFECTS
======================================== */
function handleScroll() {
const scrollY = window.scrollY;

/* NAVBAR */
if (nav) {
nav.style.background = "rgba(0,0,0,.85)";
}

/* HERO PARALLAX */
if(
heroImage &&
window.innerWidth > 1024
){
heroImage.style.transform =
`translateY(${scrollY * 0.12}px) scale(1.05)`;
}

const navLinks =
document.querySelectorAll(
".side-links a"
);

/* HERO TITLE FADE */
if (heroTitle) {
const opacity = 1 - scrollY / 400;
heroTitle.style.opacity =
Math.max(opacity, 0);
}

/* ACTIVE NAVIGATION */
let current = "";
sections.forEach(section => {
const sectionTop = section.offsetTop - 200;
if (scrollY >= sectionTop) {
current = section.getAttribute("id");
}
});

navLinks.forEach(link => {
link.classList.remove("active");
if (
link.getAttribute("href") === `#${current}`
) {
link.classList.add("active");
}
});
}

/* ========================================
OPTIMIZED SCROLL
======================================== */
let ticking = false;
window.addEventListener("scroll", () => {
if (!ticking) {
window.requestAnimationFrame(() => {
handleScroll();
ticking = false;
});
ticking = true;
}
});

/* INITIAL RUN */
handleScroll();
if(
document.querySelector(".hero-title") &&
typeof gsap !== "undefined"
){
gsap.from(".hero-title",{
y:120,
duration:1.4,
ease:"power4.out"
});
}

/* ========================================
PAGE TRANSITION
======================================== */
if (transition) {
document.querySelectorAll('a[href$=".html"]').forEach(link => {
const href = link.getAttribute("href");
const isInternal =
href &&
!href.startsWith("#") &&
!href.startsWith("mailto") &&
!href.startsWith("http");
if (!isInternal) return;
link.addEventListener("click", e => {
e.preventDefault();
if (typeof gsap !== "undefined") {
gsap.to(transition, {
opacity: 1,
duration: 0.5,
onComplete: () => {
window.location = href;
}
});
} else {
window.location = href;
}
});
});
}

window.addEventListener("pageshow", () => {
if (!transition) return;
if (typeof gsap !== "undefined") {
gsap.set(transition, {
opacity: 0
});
}
});

/* ========================================
CONSOLE MESSAGE
======================================== */
console.log(
"%cINKTENEBRIS",
`
font-size:30px;
color:white;
background:black;
padding:10px;
`
);

console.log(
"Dark Ballpoint Art by Soumalya Sarkar"
);
document.addEventListener("contextmenu", (e) => {
e.preventDefault();
});
document.querySelectorAll("img").forEach(img => {
img.setAttribute("draggable", "false");
});

/* ===================================
ABOUT ANIMATION
=================================== */
if(
document.querySelector("#about") &&
typeof gsap !== "undefined"
){
const mm = gsap.matchMedia();
mm.add("(min-width: 0px)",()=>{
const tl = gsap.timeline({
scrollTrigger:{
trigger:"#about",
start:"top 82%",
toggleActions:
"play none none reverse",
}
});

/* LEFT */
tl.from(".about-left",{
y:40,
opacity:0,
duration:1,
ease:"power3.out",
});

/* IMAGE */
tl.from(".artist-image",{
y:35,
opacity:0,
scale:.96,
duration:1.1,
ease:"power3.out",
},"-=0.7");
/* TEXT */
tl.from(".about-right p",{
y:24,
opacity:0,
stagger:.16,
duration:.9,
ease:"power2.out",
},"-=0.7");
});
}

const progress =
document.querySelector(
".scroll-progress"
);

window.addEventListener("scroll",()=>{

if(!progress) return;

const total =
document.documentElement.scrollHeight -
window.innerHeight;

const current =
window.scrollY;

const percentage =
Math.min(
(current / total) * 100,
100
);

progress.style.width =
percentage + "%";

});

if(
document.querySelector(".artwork-details h1")
&&
typeof gsap !== "undefined"
){
gsap.from(".artwork-details h1",{
y:60,
opacity:0,
duration:1.1,
ease:"power3.out"
});
}

if(
document.querySelector(".artwork-number")
&&
typeof gsap !== "undefined"
){
gsap.from(".artwork-number",{
scale:.8,
opacity:0,
duration:1.2
});
}

if(
document.querySelector(".artwork-specs")
&&
typeof gsap !== "undefined"
){
gsap.from(".spec",{
y:25,
opacity:0,
stagger:.12,
scrollTrigger:{
trigger:".artwork-specs",
start:"top 80%"
}
});
}

if(
document.querySelector(".legal-page")
&&
typeof gsap !== "undefined"
){
gsap.from(".legal-header",{
y:60,
opacity:0,
duration:1
});

gsap.from(".legal-content h2",{
y:30,
opacity:0,
stagger:.15,
scrollTrigger:{
trigger:".legal-content",
start:"top 80%"
}
});

gsap.from(".legal-content p",{
y:20,
opacity:0,
stagger:.1,
scrollTrigger:{
trigger:".legal-content",
start:"top 80%"
}
});
}

if(
document.querySelector(".preview-card")
&&
typeof gsap !== "undefined"
){
gsap.from(".preview-card",{
y:30,
opacity:0,
stagger:.15,
scrollTrigger:{
trigger:".preview-strip",
start:"top 85%"
}
});
}
