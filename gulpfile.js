const gulp = require("gulp");
const argv = require("yargs").argv;
const sourcemaps = require("gulp-sourcemaps");
const rename = require("gulp-rename");
const fs = require("fs");


// ================
// CACHE-BUSTING
// ================

const buster = require("gulp-buster");

gulp.task("cache-busting",() => {
    return gulp.src(["assets/static/assets/**/*.min.js","assets/static/assets/**/*.css"])
        .pipe(buster({
            fileName: "assets/cache_busting.json",
            relativePath: "assets/static/"
        }))
        .pipe(gulp.dest("."));
})


// ================
// BUILD-JS
// ================

const uglify = require("gulp-uglify");
const wrap = require("gulp-wrap");
const concat = require("gulp-concat");

const SUBSTITUTIONS_BUNDLE_FILES = [
    "substitutions-base.js",
    "grey-substitutions.js",
    "highlight-new-substitutions.js",
    "push-notifications.js",
    "updates.js",
    "themes.js",
    "plausible.js"
];

gulp.task("__build-js", () => {
    const srcFile = argv.srcFile;
    let destFile = argv.destFile;
    let path = argv.path;
    let s;
    let sourceMapDest = "/";
    if (SUBSTITUTIONS_BUNDLE_FILES.includes(srcFile)) {
        let paths = [];
        for (let filename of SUBSTITUTIONS_BUNDLE_FILES) paths.push((path || "assets/static/assets/js/substitutions/") + filename);
        s = gulp.src(paths);
        path = "assets/static/assets/js/";
        destFile = "substitutions.min.js";
        sourceMapDest = "/substitutions"
    } else {
        s = gulp.src((path || "assets/static/assets/js/") + srcFile);
    }
    return s
        .pipe(sourcemaps.init())
        .pipe(concat(destFile))
        .pipe(wrap('!function(){"use strict";<%= contents %>}()'))
        .pipe(uglify({
            toplevel: true
        }))
        .pipe(sourcemaps.write(sourceMapDest))
        .pipe(gulp.dest(path));
})

gulp.task("build-js", gulp.series(["__build-js", "cache-busting"]))


// ================
// BUILD-SASS
// ================

const sass = require("gulp-dart-sass");
const postcss = require("gulp-postcss");
const autoprefixer = require("autoprefixer");
const purgecss = require("@fullhuman/postcss-purgecss");
const replace = require("gulp-replace");

function getBootstrapIcon(name) {
    return fs.readFileSync("node_modules/bootstrap-icons/icons/" + name + ".svg", "utf8")
        .replace(/>\s*</g, "><")
        .replace(/"/g, "'");
}

gulp.task("__build-sass", () => {
    const srcFile = argv.srcFile;
    const path = argv.path || "assets/static/assets/style/";
    return gulp.src(path + srcFile)
        .pipe(sourcemaps.init())
        .pipe(sass({
            outputStyle: "compressed",
            outFile: path
        }))
        .pipe(postcss([
            purgecss({
                content: [
                    "assets/templates/*.min.html",
                    "assets/static/assets/*/*.min.js"
                ],
                css: [path + srcFile]
            }),
            autoprefixer()
        ]))
        .pipe(sourcemaps.write("/"))
        .pipe(replace(/!bi-([\w-]*)/g, match => getBootstrapIcon(match.substr(4))))
        .pipe(gulp.dest(path));
})

gulp.task("build-sass", gulp.series(["__build-sass", "cache-busting"]))


// ================
// MINIFY-XML
// ================

const htmlmin = require("gulp-html-minifier-terser");

gulp.task("minify-xml", () => {
    const srcFile = argv.srcFile;
    const destFile = argv.destFile;
    const path = argv.path || "assets/templates/";
    console.log(srcFile, destFile, path);
    let x = gulp.src(path + srcFile);
    if (destFile === "_base.min.html")
        x = x.pipe(replace("<!-- ###realfavicon-replace### -->", JSON.parse(fs.readFileSync(FAVICON_DATA_FILE)).favicon.html_code));
    return x.pipe(replace(/<!--bi-([\w-]*)-->/g, (m, p1) => getBootstrapIcon(p1)))
        .pipe(htmlmin({
            collapseBooleanAttributes: true,
            collapseWhitespace: true,
            removeComments: true,
            ignoreCustomFragments: [/<!--bi-([\w-]*)-->/, /<\?(.*?)\?>/]
        }))
        .pipe(rename(destFile))
        .pipe(gulp.dest(path));
});


// ================
// FAVICON GENERATOR
// ================

// the following is copied from the output of https://realfavicongenerator.net
const realFavicon = require("gulp-real-favicon");
const del = require("del");

// File where the favicon markups are stored
const FAVICON_DATA_FILE = 'dev/favicon/faviconData.json';

// Generate the icons. This task takes a few seconds to complete.
// You should run it at least once to create the icons. Then,
// you should run it whenever RealFaviconGenerator updates its
// package (see the check-for-favicon-update task below).
gulp.task('generate-favicon', done => {
    realFavicon.generateFavicon({
        // I modified the following using the information provided at
        // https://realfavicongenerator.net/api/non_interactive_api
        masterPicture: 'dev/favicon/favicon-paths-no-text.svg',
        dest: 'assets/static/',
        iconsPath: '/',
        design: {
            desktopBrowser: {
                // according to the API specification, desktop_browser is empty ...
                /*design: 'background',
                backgroundColor: '#e67b10',
                backgroundRadius: 0.45,
                imageScale: 1*/
            },
            ios: {
                masterPicture: 'dev/favicon/favicon-no-background-paths-no-text.svg',
                pictureAspect: 'backgroundAndMargin',
                backgroundColor: '#e67b10',
                margin: '11%',
                assets: {
                    ios6AndPriorIcons: false,
                    ios7AndLaterIcons: false,
                    precomposedIcons: false,
                    declareOnlyDefaultIcon: true
                },
                appName: 'GaW VPlan'
            },
            windows: {
                masterPicture: 'dev/favicon/favicon-no-background-paths-no-text.svg',
                pictureAspect: 'noChange',
                backgroundColor: '#e67b10',
                onConflict: 'override',
                assets: {
                    windows80Ie10Tile: false,
                    windows10Ie11EdgeTiles: {
                        small: false,
                        medium: true,
                        big: false,
                        rectangle: false
                    }
                },
                appName: 'GaW VPlan'
            },
            firefoxApp: {
                masterPicture: "dev/favicon/favicon-no-background-paths-no-text.svg",
                pictureAspect: "circle",
                backgroundColor: "#e67b10",
                circleInnerMargin: "8%",
                keepPictureInCircle: true,
                manifest: {
                    appName: "GaW VPlan",
                    appDescription: "Vertretungsplan für das Gymnasium am Wall Verden",
                    developerName: "Florian Rädiker",
                    developerUrl: "https://github.com/FlorianRaediker",
                    onConflict: "override"
                }
            },
            androidChrome: {
                masterPicture: 'dev/favicon/favicon-android-chrome.svg',
                pictureAspect: 'noChange',
                themeColor: '#e67b10',
                manifest: {
                    name: 'GaW VPlan',
                    display: 'standalone',
                    orientation: 'notSet',
                    themeColor: "#e67b10",
                    onConflict: 'override',
                    declared: false  // not in API specification
                },
                assets: {
                    legacyIcon: false,
                    lowResolutionIcons: false
                }
            },
            safariPinnedTab: {
                masterPicture: "dev/favicon/favicon-no-background-paths-no-text.svg",
                pictureAspect: 'silhouette',
                themeColor: '#e67b10'
            },
            openGraph: {
                pictureAspect: "noChange",
                siteUrl: "https://gawvertretung.florian-raediker.de"
            }
        },
        settings: {
            compression: 0,
            scalingAlgorithm: 'Mitchell',
            errorOnImageTooSmall: true,
            readmeFile: false,
            htmlCodeFile: false,
            usePathAsIs: false
        },
        markupFile: FAVICON_DATA_FILE
    }, function() {
        del("assets/static/site.webmanifest") // webmanifest as generated by realfavicon is in the wrong place
        done();
    });
});

// the following is done automatically in minify-xml when _base.html is minified
/*// Inject the favicon markups in your HTML pages. You should run
// this task whenever you modify a page. You can keep this task
// as is or refactor your existing HTML pipeline.
gulp.task('inject-favicon-markups', function() {
	return gulp.src([ 'assets/templates/_base.html' ])
		.pipe(realFavicon.injectFaviconMarkups(JSON.parse(fs.readFileSync(FAVICON_DATA_FILE)).favicon.html_code))
		.pipe(gulp.dest('assets/templates/'));
});*/

// Check for updates on RealFaviconGenerator (think: Apple has just
// released a new Touch icon along with the latest version of iOS).
// Run this task from time to time. Ideally, make it part of your
// continuous integration system.
gulp.task('check-for-favicon-update', done => {
    let currentVersion = JSON.parse(fs.readFileSync(FAVICON_DATA_FILE)).version;
    realFavicon.checkForUpdates(currentVersion, function(err) {
        if (err) {
            throw err;
        }
        done();
    });
});
