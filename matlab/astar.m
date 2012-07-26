function x_hat = astar(Phi, y, K, P)

[~, N] = size(Phi);


%A*OMP options
%options, may be omitted
options.I = 3;  % I>=1
options.B = 2;  % B>=1
options.P = P;   % P>=1
options.alpha = 0.75;
options.beta = 1.2;
options.AuxMode = 'Mul'; %possible: 'Add','Adap', 'Mul'
options.Control = 'On';  %possible: 'On'/'Off'
options.Display = 'Off';  %possible: 'On'/'Off'

% run A*OMP
x_hat = AStarOMP(y, Phi, N, K, options);

