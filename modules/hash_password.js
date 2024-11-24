//var Key="e=10001;m=d0fa1d37fa0bb621a8cbb6669249ba1d14bbd5058592f050240d8c3b68674f0e28283018a7753f4377aaa3b3645e5f119a0032129a0a64322f74888aed3519de49e98c5b3c221460218140616f01ac5e9f2f8042e2749b8a89112f15310690dad7531f6758c0c65e525dff7859283b566a5b154352c57161cd24e59133a61432f461583e40cac749d722909dfcf0edd6af3cbc9a25e639b0caaf55e8c7b08b53c7d52038b48e1b26ad40f8bb84b3bb9c92bc9b947d2ab5ae4664a5093a4895af09659a78c9393797ea76b5b9416a45025e2ab3ea1627f08d85abd22e156d3e842efbaa1d0e1e4885028b2bc0aa7be8e444799e96fce0444f2b56bd14c0244b4d";
//var randomNum="16537382A7643C48EB39F7FDC4EEEC9B71CA506D8E0A6F7F5D4D927E848AB1267CBAFD451B4C4F9E1B0E27502D330FE7DABC7E7411505D8D548838B1A6055DAE7B2365883B62038F658BA4B72568A8A2E21BB0B391BB76018A1B3710F6BB3AD30869CB75";
//var SKI="AF99E0B5CB4A0FCD26625571F926665CC11334CE";
//var hash_type = 'saproof';
//var password = '111111';

var Key = process.argv[2];
var randomNum = process.argv[3];
var hash_type = process.argv[4];
var password = process.argv[5];

if (Key == 'khongco')
    {Key="e=10001;m=d0fa1d37fa0bb621a8cbb6669249ba1d14bbd5058592f050240d8c3b68674f0e28283018a7753f4377aaa3b3645e5f119a0032129a0a64322f74888aed3519de49e98c5b3c221460218140616f01ac5e9f2f8042e2749b8a89112f15310690dad7531f6758c0c65e525dff7859283b566a5b154352c57161cd24e59133a61432f461583e40cac749d722909dfcf0edd6af3cbc9a25e639b0caaf55e8c7b08b53c7d52038b48e1b26ad40f8bb84b3bb9c92bc9b947d2ab5ae4664a5093a4895af09659a78c9393797ea76b5b9416a45025e2ab3ea1627f08d85abd22e156d3e842efbaa1d0e1e4885028b2bc0aa7be8e444799e96fce0444f2b56bd14c0244b4d"}

if (randomNum == 'khongco')
    {randomNum="16537382A7643C48EB39F7FDC4EEEC9B71CA506D8E0A6F7F5D4D927E848AB1267CBAFD451B4C4F9E1B0E27502D330FE7DABC7E7411505D8D548838B1A6055DAE7B2365883B62038F658BA4B72568A8A2E21BB0B391BB76018A1B3710F6BB3AD30869CB75"}

function Encrypt(e,t,n,a){var o=[];switch(n.toLowerCase()){case"chgsqsa":if(null==e||null==t){return null}o=PackageSAData(e,t);break;case"chgpwd":if(null==e||null==a){return null}o=PackageNewAndOldPwd(e,a);break;case"pwd":if(null==e){return null}o=PackagePwdOnly(e);break;case"pin":if(null==e){return null}o=PackagePinOnly(e);break;case"proof":if(null==e&&null==t){return null}o=PackageLoginIntData(null!=e?e:t);break;case"saproof":if(null==t){return null}o=PackageSADataForProof(t);break;case"newpwd":if(null==a){return null}o=PackageNewPwdOnly(a)}if(null==o||"undefined"==typeof o){return o}if("undefined"!=typeof Key&&void 0!==parseRSAKeyFromString){var i=parseRSAKeyFromString(Key)}var r=RSAEncrypt(o,i,randomNum);return r}function PackageSAData(e,t){var n=[],a=0;n[a++]=1,n[a++]=1,n[a++]=0;var o,i=t.length;for(n[a++]=2*i,o=0;i>o;o++){n[a++]=255&t.charCodeAt(o),n[a++]=(65280&t.charCodeAt(o))>>8}var r=e.length;for(n[a++]=r,o=0;r>o;o++){n[a++]=127&e.charCodeAt(o)}return n}

function PackagePwdOnly(e){var t=[],n=0;t[n++]=1,t[n++]=1,t[n++]=0,t[n++]=0;var a,o=e.length;for(t[n++]=o,a=0;o>a;a++){t[n++]=127&e.charCodeAt(a)}return t}

function PackagePinOnly(e){var t=[],n=0;t[n++]=1,t[n++]=2,t[n++]=0,t[n++]=0,t[n++]=0;var a,o=e.length;for(t[n++]=o,a=0;o>a;a++){t[n++]=127&e.charCodeAt(a)}return t}

function PackageLoginIntData(e){var t,n=[],a=0;for(t=0;t<e.length;t++){n[a++]=255&e.charCodeAt(t),n[a++]=(65280&e.charCodeAt(t))>>8}return n}

function PackageSADataForProof(e){var t,n=[],a=0;for(t=0;t<e.length;t++){n[a++]=127&e.charCodeAt(t),n[a++]=(65280&e.charCodeAt(t))>>8}return n}

function PackageNewPwdOnly(e){var t=[],n=0;t[n++]=1,t[n++]=1;var a,o=e.length;for(t[n++]=o,a=0;o>a;a++){t[n++]=127&e.charCodeAt(a)}return t[n++]=0,t[n++]=0,t}

function PackageNewAndOldPwd(e,t){var n=[],a=0;n[a++]=1,n[a++]=1;var o,i=t.length;for(n[a++]=i,o=0;i>o;o++){n[a++]=127&t.charCodeAt(o)}for(n[a++]=0,i=e.length,n[a++]=i,o=0;i>o;o++){n[a++]=127&e.charCodeAt(o)}return n}

function mapByteToBase64(e){return e>=0&&26>e?String.fromCharCode(65+e):e>=26&&52>e?String.fromCharCode(97+e-26):e>=52&&62>e?String.fromCharCode(48+e-52):62==e?"+":"/"}

function base64Encode(e,t){var n,a="";for(n=t;4>n;n++){e>>=6}for(n=0;t>n;n++){a=mapByteToBase64(63&e)+a,e>>=6}return a}

function byteArrayToBase64(e){var t,n,a=e.length,o="";for(t=a-3;t>=0;t-=3){n=e[t]|e[t+1]<<8|e[t+2]<<16,o+=base64Encode(n,4)}var i=a%3;for(n=0,t+=2;t>=0;t--){n=n<<8|e[t]}return 1==i?o=o+base64Encode(n<<16,2)+"==":2==i&&(o=o+base64Encode(n<<8,3)+"="),o}

function parseRSAKeyFromString(e){var t=e.indexOf(";");if(0>t){return null}var n=e.substr(0,t),a=e.substr(t+1),o=n.indexOf("=");if(0>o){return null}var i=n.substr(o+1);if(o=a.indexOf("="),0>o){return null}var r=a.substr(o+1),s=new Object;return s.n=hexStringToMP(r),s.e=parseInt(i,16),s}

function RSAEncrypt(e,t){for(var n=[],a=42,o=2*t.n.size-a,i=0;i<e.length;i+=o){if(i+o>=e.length){var r=RSAEncryptBlock(e.slice(i),t,randomNum);r&&(n=r.concat(n))}else{var r=RSAEncryptBlock(e.slice(i,i+o),t,randomNum);r&&(n=r.concat(n))}}var s=byteArrayToBase64(n);return s}

function RSAEncryptBlock(e,t,n){var a=t.n,o=t.e,i=e.length,r=2*a.size,s=42;if(i+s>r){return null}applyPKCSv2Padding(e,r,n),e=e.reverse();var l=byteArrayToMP(e),d=modularExp(l,o,a);d.size=a.size;var c=mpToByteArray(d);return c=c.reverse()}

function JSMPnumber(){this.size=1,this.data=[],this.data[0]=0}function duplicateMP(e){var t=new JSMPnumber;return t.size=e.size,t.data=e.data.slice(0),t}

function byteArrayToMP(e){var t=new JSMPnumber,n=0,a=e.length,o=a>>1;for(n=0;o>n;n++){t.data[n]=e[2*n]+(e[1+2*n]<<8)}return a%2&&(t.data[n++]=e[a-1]),t.size=n,t}

function mpToByteArray(e){var t=[],n=0,a=e.size;for(n=0;a>n;n++){t[2*n]=255&e.data[n];var o=e.data[n]>>>8;t[2*n+1]=o}return t}

function modularExp(e,t,n){for(var a=[],o=0;t>0;){a[o]=1&t,t>>>=1,o++}for(var i=duplicateMP(e),r=o-2;r>=0;r--){i=modularMultiply(i,i,n),1==a[r]&&(i=modularMultiply(i,e,n))}return i}

function modularMultiply(e,t,n){var a=multiplyMP(e,t),o=divideMP(a,n);return o.r}

function multiplyMP(e,t){var n=new JSMPnumber;n.size=e.size+t.size;var a,o;for(a=0;a<n.size;a++){n.data[a]=0}var i=e.data,r=t.data,s=n.data;if(e==t){for(a=0;a<e.size;a++){s[2*a]+=i[a]*i[a]}for(a=1;a<e.size;a++){for(o=0;a>o;o++){s[a+o]+=2*i[a]*i[o]}}}else{for(a=0;a<e.size;a++){for(o=0;o<t.size;o++){s[a+o]+=i[a]*r[o]}}}return normalizeJSMP(n),n}

function normalizeJSMP(e){var t,n,a,o,i;for(a=e.size,n=0,t=0;a>t;t++){o=e.data[t],o+=n,i=o,n=Math.floor(o/65536),o-=65536*n,e.data[t]=o}}

function removeLeadingZeroes(e){for(var t=e.size-1;t>0&&0==e.data[t--];){e.size--}}

function divideMP(e,t){var n=e.size,a=t.size,o=t.data[a-1],i=t.data[a-1]+t.data[a-2]/65536,r=new JSMPnumber;r.size=n-a+1,e.data[n]=0;for(var s=n-1;s>=a-1;s--){var l=s-a+1,d=Math.floor((65536*e.data[s+1]+e.data[s])/i);if(d>0){var c=multiplyAndSubtract(e,d,t,l);for(0>c&&(d--,multiplyAndSubtract(e,d,t,l));c>0&&e.data[s]>=o;){c=multiplyAndSubtract(e,1,t,l),c>0&&d++}}r.data[l]=d}removeLeadingZeroes(e);var u={"q":r,"r":e};return u}

function multiplyAndSubtract(e,t,n,a){var o,i=e.data.slice(0),r=0,s=e.data;for(o=0;o<n.size;o++){var l=r+n.data[o]*t;r=l>>>16,l-=65536*r,l>s[o+a]?(s[o+a]+=65536-l,r++):s[o+a]-=l}return r>0&&(s[o+a]-=r),s[o+a]<0?(e.data=i.slice(0),-1):1}

function applyPKCSv2Padding(e,t,n){var a,o=e.length,i=[218,57,163,238,94,107,75,13,50,85,191,239,149,96,24,144,175,216,7,9],r=t-o-40-2,s=[];for(a=0;r>a;a++){s[a]=0}s[r]=1;var l=i.concat(s,e),d=[];for(a=0;20>a;a++){d[a]=Math.floor(256*Math.random())}d=SHA1(d.concat(n));var c=MGF(d,t-21),u=XORarrays(l,c),p=MGF(u,20),m=XORarrays(d,p),g=[];for(g[0]=0,g=g.concat(m,u),a=0;a<g.length;a++){e[a]=g[a]}}

function MGF(e,t){if(t>4096){return null}var n=e.slice(0),a=n.length;n[a++]=0,n[a++]=0,n[a++]=0,n[a]=0;for(var o=0,i=[];i.length<t;){n[a]=o++,i=i.concat(SHA1(n))}return i.slice(0,t)}

function XORarrays(e,t){if(e.length!=t.length){return null}for(var n=[],a=e.length,o=0;a>o;o++){n[o]=e[o]^t[o]}return n}

function SHA1(e){var t,n=e.slice(0);PadSHA1Input(n);var a={"A":1732584193,"B":4023233417,"C":2562383102,"D":271733878,"E":3285377520};for(t=0;t<n.length;t+=64){SHA1RoundFunction(a,n,t)}var o=[];return wordToBytes(a.A,o,0),wordToBytes(a.B,o,4),wordToBytes(a.C,o,8),wordToBytes(a.D,o,12),wordToBytes(a.E,o,16),o}

function wordToBytes(e,t,n){var a;for(a=3;a>=0;a--){t[n+a]=255&e,e>>>=8}}

function PadSHA1Input(e){var t,n=e.length,a=n,o=n%64,i=55>o?56:120;for(e[a++]=128,t=o+1;i>t;t++){e[a++]=0}var r=8*n;for(t=1;8>t;t++){e[a+8-t]=255&r,r>>>=8}}

function SHA1RoundFunction(e,t,n){var a,o,i,r=1518500249,s=1859775393,l=2400959708,d=3395469782,c=[],u=e.A,p=e.B,m=e.C,g=e.D,f=e.E;for(o=0,i=n;16>o;o++,i+=4){c[o]=t[i]<<24|t[i+1]<<16|t[i+2]<<8|t[i+3]<<0}for(o=16;80>o;o++){c[o]=rotateLeft(c[o-3]^c[o-8]^c[o-14]^c[o-16],1)}var v;for(a=0;20>a;a++){v=rotateLeft(u,5)+(p&m|~p&g)+f+c[a]+r&4294967295,f=g,g=m,m=rotateLeft(p,30),p=u,u=v}for(a=20;40>a;a++){v=rotateLeft(u,5)+(p^m^g)+f+c[a]+s&4294967295,f=g,g=m,m=rotateLeft(p,30),p=u,u=v}for(a=40;60>a;a++){v=rotateLeft(u,5)+(p&m|p&g|m&g)+f+c[a]+l&4294967295,f=g,g=m,m=rotateLeft(p,30),p=u,u=v}for(a=60;80>a;a++){v=rotateLeft(u,5)+(p^m^g)+f+c[a]+d&4294967295,f=g,g=m,m=rotateLeft(p,30),p=u,u=v}e.A=e.A+u&4294967295,e.B=e.B+p&4294967295,e.C=e.C+m&4294967295,e.D=e.D+g&4294967295,e.E=e.E+f&4294967295}

function rotateLeft(e,t){var n=e>>>32-t,a=(1<<32-t)-1,o=e&a;return o<<t|n}

function hexStringToMP(e){var t,n,a=Math.ceil(e.length/4),o=new JSMPnumber;for(o.size=a,t=0;a>t;t++){n=e.substr(4*t,4),o.data[a-1-t]=parseInt(n,16)}return o}

if(hash_type == 'newpwd')
    {CipherValue=Encrypt(null, null, hash_type, password)}

if(hash_type == 'saproof')
    {CipherValue=Encrypt(null, password, hash_type, null)}


console.log(CipherValue); //123