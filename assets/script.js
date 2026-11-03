"use strict";

if ("IntersectionObserver" in window) {
  document.documentElement.classList.add("js");
}

if (typeof gsap !== "undefined" && typeof ScrollTrigger !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

const nav = document.querySelector("nav");
const heroImage = document.querySelector(".hero-image");
const heroTitle = document.querySelector(".hero-title");
const transition = document.getElementById("page-transition");
const infoToggle = document.querySelector(".info-toggle");
const infoPanel = document.querySelector(".info-panel");
const sections = document.querySelectorAll("section[id]");
const navLinks = document.querySelectorAll(".side-links a");
const revealItems = document.querySelectorAll(".artwork");
const progress = document.querySelector(".scroll-progress");

window.addEventListener("load", () => {
  const loader = document.getElementById("loader");

  if (!loader) return;

  const fallback = setTimeout(() => {
    loader.style.display = "none";
  }, 3000);

  if (typeof gsap !== "undefined") {
    const tl = gsap.timeline();

    tl.to("#loader span", {
      opacity: 1,
      duration: 0.4,
    }).to(loader, {
      opacity: 0,
      duration: 0.5,
      delay: 0.2,
      onComplete: () => {
        clearTimeout(fallback);
        loader.style.display = "none";
      },
    });
  }
});

const observer =
  "IntersectionObserver" in window &&
  new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("show");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.1,
      rootMargin: "0px 0px -80px 0px",
    },
  );
if (observer) revealItems.forEach((item) => observer.observe(item));

if (typeof gsap !== "undefined" && typeof ScrollTrigger !== "undefined") {
  gsap.utils
    .toArray(
      ".intro, .split-showcase, .exhibition-intro, .manifesto, #about, #instagram, #contact, #updates, .fullscreen-artwork",
    )
    .forEach((section) => {
      gsap.from(section, {
        opacity: 0,
        y: 60,
        duration: 0.8,
        ease: "power4.out",
        scrollTrigger: {
          trigger: section,
          start: "top 85%",
        },
      });
    });
}

function updateScrollProgress() {
  if (!progress) return;
  const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
  const percentage = maxScroll ? (Math.min(Math.max(window.scrollY, 0), maxScroll) / maxScroll) * 100 : 0;
  progress.style.width = `${percentage}%`;
}

function handleScroll() {
  const scrollY = window.scrollY;
  updateScrollProgress();

  if (nav) {
    nav.style.background = "rgba(0,0,0,.85)";
  }

  if (heroImage && window.innerWidth > 1024) {
    heroImage.style.transform = `translateY(${scrollY * 0.12}px) scale(1.05)`;
  }

  if (heroTitle) {
    const opacity = 1 - scrollY / 400;
    heroTitle.style.opacity = Math.max(opacity, 0);
  }

  let current = "";
  sections.forEach((section) => {
    const sectionTop = section.offsetTop - 200;
    if (scrollY >= sectionTop) {
      current = section.getAttribute("id");
    }
  });

  navLinks.forEach((link) => {
    link.classList.remove("active");
    if (link.getAttribute("href") === `#${current}`) {
      link.classList.add("active");
    }
  });
}

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

handleScroll();
if (document.querySelector(".hero-title") && typeof gsap !== "undefined") {
  gsap.from(".hero-title", {
    y: 120,
    duration: 1.4,
    ease: "power4.out",
  });
}

if (transition) {
  document.querySelectorAll('a[href]').forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute("download")) return;
      const destination = new URL(link.href, window.location.href);
      if (destination.origin !== window.location.origin || !destination.pathname.endsWith(".html") || destination.pathname === window.location.pathname) return;
      event.preventDefault();
      const navigate = () => window.location.assign(destination.href);
      if (typeof gsap !== "undefined") gsap.to(transition, { opacity: 1, duration: 0.5, onComplete: navigate });
      else navigate();
    });
  });
}

if (infoToggle && infoPanel) {
  const closeInfo = () => {
    infoToggle.setAttribute("aria-expanded", "false");
    infoPanel.hidden = true;
  };

  infoToggle.addEventListener("click", () => {
    const isOpen = infoToggle.getAttribute("aria-expanded") === "true";
    infoToggle.setAttribute("aria-expanded", String(!isOpen));
    infoPanel.hidden = isOpen;
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".info-menu")) closeInfo();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeInfo();
  });
}

window.addEventListener("pageshow", () => {
  if (!transition) return;
  if (typeof gsap !== "undefined") gsap.set(transition, { opacity: 0 });
  else transition.style.opacity = "0";
});

console.log(
  "%cINKTENEBRIS",
  `
font-size:30px;
color:white;
background:black;
padding:10px;
`,
);

console.log("Dark Ballpoint Art by Soumalya Sarkar");
document.querySelectorAll("img").forEach((img) => {
  img.setAttribute("draggable", "false");
});

if (document.querySelector("#about") && typeof gsap !== "undefined") {
  const mm = gsap.matchMedia();
  mm.add("(min-width: 0px)", () => {
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: "#about",
        start: "top 82%",
        toggleActions: "play none none reverse",
      },
    });

    tl.from(".about-left", {
      y: 40,
      opacity: 0,
      duration: 1,
      ease: "power3.out",
    });

    tl.from(
      ".artist-image",
      {
        y: 35,
        opacity: 0,
        scale: 0.96,
        duration: 1.1,
        ease: "power3.out",
      },
      "-=0.7",
    );

    tl.from(
      ".about-right p",
      {
        y: 24,
        opacity: 0,
        stagger: 0.16,
        duration: 0.9,
        ease: "power2.out",
      },
      "-=0.7",
    );
  });
}


if (
  document.querySelector(".artwork-details h1") &&
  typeof gsap !== "undefined"
) {
  gsap.from(".artwork-details h1", {
    y: 60,
    opacity: 0,
    duration: 1.1,
    ease: "power3.out",
  });
}

if (document.querySelector(".artwork-number") && typeof gsap !== "undefined") {
  gsap.from(".artwork-number", {
    scale: 0.8,
    opacity: 0,
    duration: 1.2,
  });
}

if (document.querySelector(".artwork-specs") && typeof gsap !== "undefined") {
  gsap.from(".spec", {
    y: 25,
    opacity: 0,
    stagger: 0.12,
    scrollTrigger: {
      trigger: ".artwork-specs",
      start: "top 80%",
    },
  });
}

if (document.querySelector(".legal-page") && typeof gsap !== "undefined") {
  gsap.from(".legal-header", {
    y: 60,
    opacity: 0,
    duration: 1,
  });

  gsap.from(".legal-content h2", {
    y: 30,
    opacity: 0,
    stagger: 0.15,
    scrollTrigger: {
      trigger: ".legal-content",
      start: "top 80%",
    },
  });

  gsap.from(".legal-content p", {
    y: 20,
    opacity: 0,
    stagger: 0.1,
    scrollTrigger: {
      trigger: ".legal-content",
      start: "top 80%",
    },
  });
}

if (document.querySelector(".preview-card") && typeof gsap !== "undefined") {
  gsap.from(".preview-card", {
    y: 30,
    opacity: 0,
    stagger: 0.15,
    scrollTrigger: {
      trigger: ".preview-strip",
      start: "top 85%",
    },
  });
}
