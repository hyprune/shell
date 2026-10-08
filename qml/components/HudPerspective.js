// P * Rz * Ry * Rx, conjugated about the outside edge. Positive depth approaches
// the viewer: inner edges come forward, outer edges recede on convex glass.
function multiply(a,b) {
    var out = [];
    for (var r=0;r<4;r++) for (var c=0;c<4;c++) {
        var n=0;for (var k=0;k<4;k++) n+=a[r*4+k]*b[k*4+c];out.push(n);
    }
    return out;
}
function translation(x,y) { return [1,0,0,x,0,1,0,y,0,0,1,0,0,0,0,1]; }
function matrix(width,height,edgeX,edgeY,strength) {
    // At the default 80%, a 590x203 deck has ~3.2/2.4 degree rising borders
    // and an inner edge ~4.9% taller. Calibrated to measured gameplay rules.
    var yaw=edgeX*16*strength*Math.PI/180,pitch=-edgeY*16*strength*Math.PI/180;
    var cy=Math.cos(yaw),sy=Math.sin(yaw),cx=Math.cos(pitch),sx=Math.sin(pitch);
    var ox=edgeX<0?0:edgeX>0?width:width/2,oy=height/2,d=Math.max(500,width*5);
    var ry=[cy,0,sy,0,0,1,0,0,-sy,0,cy,0,0,0,0,1];
    var rx=[1,0,0,0,0,cx,-sx,0,0,sx,cx,0,0,0,0,1];
    // The tangent leans inward at each corner. Keep this independent of the
    // yaw/pitch cross term, which otherwise reverses the apparent border slope.
    var roll=edgeX*edgeY*3.5*strength*Math.PI/180,cr=Math.cos(roll),sr=Math.sin(roll);
    var rz=[cr,-sr,0,0,sr,cr,0,0,0,0,1,0,0,0,0,1];
    var p=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,-1/d,1];
    var m=multiply(translation(ox,oy),multiply(p,multiply(rz,multiply(ry,multiply(rx,translation(-ox,-oy))))));
    // Preserve the projective divide but flatten output depth for the 2D
    // scenegraph clip volume. The projected plane itself remains unchanged.
    m[8]=0; m[9]=0; m[10]=1; m[11]=0;
    return Qt.matrix4x4(m[0],m[1],m[2],m[3],m[4],m[5],m[6],m[7],m[8],m[9],m[10],m[11],m[12],m[13],m[14],m[15]);
}
